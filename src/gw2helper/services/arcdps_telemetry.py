"""Real-time combat telemetry from the ArcDPS BHud bridge."""

from __future__ import annotations

import socket
import struct
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Mapping, Optional

import psutil

from .gw2_api import Gw2ApiClient, SkillMetadata

_BHUD_UI_MESSAGE = 1
_BHUD_COMBAT_MESSAGE = 2
_BHUD_COMBAT_LOCAL_MESSAGE = 3
_BHUD_PORT_MASK = (1 << 14) | (1 << 15)
_BHUD_MAX_FRAME_SIZE = 65_536
_BHUD_RECONNECT_SECONDS = 1.0
_HUD_SCAN_SECONDS = 0.45
_MAX_EVENT_AGE_SECONDS = 10.0

_CBTS_BUFFINITIAL = 18
_CBTS_ANIMATIONSTART = 67
_CBTS_BUFFAPPLY = 69
_CBTS_BUFFCHANGE = 70
_CBTS_BUFFREMOVE_SINGLE = 71
_CBTS_BUFFREMOVE_ALL = 72

_KNOWN_BUFF_NAMES = {
    717: "Protection",
    718: "Regeneration",
    719: "Swiftness",
    725: "Fury",
    726: "Vigor",
    740: "Might",
    743: "Aegis",
    873: "Resolution",
    1187: "Quickness",
    30328: "Alacrity",
}
_KNOWN_BUFF_IDS = {name.casefold(): skill_id for skill_id, name in _KNOWN_BUFF_NAMES.items()}

_SLOT_LABELS = {
    "Weapon_2": "Weapon 2",
    "Weapon_3": "Weapon 3",
    "Weapon_4": "Weapon 4",
    "Weapon_5": "Weapon 5",
    "Profession_1": "F1",
    "Profession_2": "F2",
    "Profession_3": "F3",
    "Profession_4": "F4",
    "Profession_5": "F5",
    "Heal": "Heal",
    "Elite": "Elite",
    "WeaponSwap": "Weapon Swap",
}


class BHudProtocolError(ValueError):
    """Raised when a frame does not match BHud's documented bincode protocol."""


@dataclass(frozen=True)
class ArcDpsAgent:
    name: Optional[str]
    agent_id: int
    profession: int
    elite_specialization: int
    is_self: bool
    team: int


@dataclass(frozen=True)
class ArcDpsCombatEvent:
    time_ms: int
    source_agent: int
    destination_agent: int
    value: int
    buff_damage: int
    overstack_value: int
    skill_id: int
    source_instance_id: int
    destination_instance_id: int
    source_master_instance_id: int
    destination_master_instance_id: int
    iff: int
    buff: int
    result: int
    activation: int
    buff_remove: int
    is_ninety: int
    is_fifty: int
    is_moving: int
    statechange: int
    is_flanking: int
    is_shields: int
    is_off_cycle: int
    pad61: int
    pad62: int
    pad63: int
    pad64: int

    @property
    def track_id(self) -> int:
        return self.pad61 | (self.pad62 << 8) | (self.pad63 << 16) | (self.pad64 << 24)


@dataclass(frozen=True)
class ArcDpsCombatMessage:
    event: Optional[ArcDpsCombatEvent]
    source: Optional[ArcDpsAgent]
    destination: Optional[ArcDpsAgent]
    skill_name: Optional[str]
    event_id: int
    revision: int
    is_local: bool


@dataclass(frozen=True)
class ActiveBuff:
    skill_id: int
    name: str
    stacks: int
    remaining_seconds: Optional[float]


@dataclass(frozen=True)
class SkillCooldown:
    skill_id: Optional[int]
    name: str
    slot: Optional[str]
    ready: Optional[bool]
    remaining_seconds: Optional[float]


@dataclass(frozen=True)
class CombatTelemetrySnapshot:
    bridge_status: str
    character_loaded: Optional[bool]
    skills: tuple[SkillCooldown, ...]
    buffs: tuple[ActiveBuff, ...]


@dataclass
class _BuffStack:
    track_id: int
    expires_at: Optional[float]


@dataclass
class _SkillRecord:
    skill_id: int
    activated_at: float
    metadata: Optional[SkillMetadata] = None


class _BincodeReader:
    """Reader for BHud's bincode 1.x varint payloads."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def byte(self) -> int:
        if self._offset >= len(self._data):
            raise BHudProtocolError("Unexpected end of BHud frame.")
        value = self._data[self._offset]
        self._offset += 1
        return value

    def unsigned(self) -> int:
        marker = self.byte()
        if marker < 251:
            return marker
        lengths = {251: 2, 252: 4, 253: 8, 254: 16}
        length = lengths.get(marker)
        if length is None or self.remaining < length:
            raise BHudProtocolError("Invalid BHud variable-length integer.")
        value = int.from_bytes(
            self._data[self._offset : self._offset + length],
            "little",
        )
        self._offset += length
        return value

    def signed(self) -> int:
        value = self.unsigned()
        return (value >> 1) ^ -(value & 1)

    def option(self) -> bool:
        value = self.byte()
        if value not in {0, 1}:
            raise BHudProtocolError("Invalid BHud option discriminator.")
        return bool(value)

    def boolean(self) -> bool:
        value = self.byte()
        if value not in {0, 1}:
            raise BHudProtocolError("Invalid BHud boolean value.")
        return bool(value)

    def string(self) -> str:
        length = self.unsigned()
        if self.remaining < length:
            raise BHudProtocolError("Invalid BHud string length.")
        value = self._data[self._offset : self._offset + length]
        self._offset += length
        return value.decode("utf-8", "replace")

    def agent(self) -> Optional[ArcDpsAgent]:
        if not self.option():
            return None
        name = self.string() if self.option() else None
        return ArcDpsAgent(
            name=name,
            agent_id=self.unsigned(),
            profession=self.unsigned(),
            elite_specialization=self.unsigned(),
            is_self=bool(self.unsigned()),
            team=self.unsigned(),
        )

    def event(self) -> Optional[ArcDpsCombatEvent]:
        if not self.option():
            return None
        time_ms = self.unsigned()
        source_agent = self.unsigned()
        destination_agent = self.unsigned()
        value = self.signed()
        buff_damage = self.signed()
        overstack_value = self.unsigned()
        skill_id = self.unsigned()
        source_instance_id = self.unsigned()
        destination_instance_id = self.unsigned()
        source_master_instance_id = self.unsigned()
        destination_master_instance_id = self.unsigned()
        flags = [self.byte() for _ in range(16)]
        return ArcDpsCombatEvent(
            time_ms=time_ms,
            source_agent=source_agent,
            destination_agent=destination_agent,
            value=value,
            buff_damage=buff_damage,
            overstack_value=overstack_value,
            skill_id=skill_id,
            source_instance_id=source_instance_id,
            destination_instance_id=destination_instance_id,
            source_master_instance_id=source_master_instance_id,
            destination_master_instance_id=destination_master_instance_id,
            iff=flags[0],
            buff=flags[1],
            result=flags[2],
            activation=flags[3],
            buff_remove=flags[4],
            is_ninety=flags[5],
            is_fifty=flags[6],
            is_moving=flags[7],
            statechange=flags[8],
            is_flanking=flags[9],
            is_shields=flags[10],
            is_off_cycle=flags[11],
            pad61=flags[12],
            pad62=flags[13],
            pad63=flags[14],
            pad64=flags[15],
        )

    def combat_message(self, is_local: bool) -> ArcDpsCombatMessage:
        message = ArcDpsCombatMessage(
            event=self.event(),
            source=self.agent(),
            destination=self.agent(),
            skill_name=self.string() if self.option() else None,
            event_id=self.unsigned(),
            revision=self.unsigned(),
            is_local=is_local,
        )
        if self.remaining:
            raise BHudProtocolError("Unexpected bytes at the end of BHud combat frame.")
        return message


def bhud_port_for_pid(process_id: int) -> int:
    """Return the BHud v2 port derived from a Guild Wars 2 process ID."""

    return (((process_id & 0xFFFF) + 1) & 0xFFFF) | _BHUD_PORT_MASK


def decode_bhud_payload(payload: bytes) -> tuple[Optional[bool], Optional[ArcDpsCombatMessage]]:
    """Decode one BHud framed payload into UI state or a combat event message."""

    if not payload:
        raise BHudProtocolError("Empty BHud payload.")
    message_id = payload[0]
    reader = _BincodeReader(payload[1:])
    if message_id == _BHUD_UI_MESSAGE:
        if reader.remaining != 1:
            raise BHudProtocolError("Invalid BHud UI message.")
        return reader.boolean(), None
    if message_id in {_BHUD_COMBAT_MESSAGE, _BHUD_COMBAT_LOCAL_MESSAGE}:
        return None, reader.combat_message(message_id == _BHUD_COMBAT_LOCAL_MESSAGE)
    return None, None


class ArcDpsCombatMonitor:
    """Maintains live buff and cooldown state from BHud and action-bar checks."""

    def __init__(
        self,
        *,
        hud_supplier: Optional[Callable[[], Mapping[str, bool]]] = None,
        skill_lookup: Optional[Callable[[int], Optional[SkillMetadata]]] = None,
        process_id_supplier: Optional[Callable[[], Optional[int]]] = None,
        clock: Callable[[], float] = time.monotonic,
        asynchronous_skill_lookup: bool = True,
    ) -> None:
        self._hud_supplier = hud_supplier
        self._skill_lookup = skill_lookup or _lookup_skill_metadata
        self._process_id_supplier = process_id_supplier or _find_gw2_process_id
        self._clock = clock
        self._asynchronous_skill_lookup = asynchronous_skill_lookup
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._bridge_status = "ArcDPS bridge unavailable"
        self._character_loaded: Optional[bool] = None
        self._self_agent_ids: set[int] = set()
        self._buffs: dict[int, list[_BuffStack]] = {}
        self._buff_names: dict[int, str] = {}
        self._skill_records: dict[int, _SkillRecord] = {}
        self._hud_ready: dict[str, bool] = {}
        self._hud_buffs: dict[str, bool] = {}
        self._skill_lookups_in_progress: set[int] = set()
        self._seen_event_ids: OrderedDict[
            tuple[int, int, int, int, int, int, int],
            None,
        ] = OrderedDict()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

    def snapshot(self) -> CombatTelemetrySnapshot:
        with self._lock:
            now = self._clock()
            self._expire_buffs(now)
            return CombatTelemetrySnapshot(
                bridge_status=self._bridge_status,
                character_loaded=self._character_loaded,
                skills=tuple(self._build_skill_snapshot(now)),
                buffs=tuple(self._build_buff_snapshot(now)),
            )

    def ingest_payload(self, payload: bytes) -> None:
        ui_state, combat_message = decode_bhud_payload(payload)
        with self._lock:
            if ui_state is not None:
                self._character_loaded = ui_state
            if combat_message is not None:
                self._ingest_combat_message(combat_message)

    def update_hud_status(self, status: Mapping[str, bool]) -> None:
        """Update action-bar readiness and visual fallback buff observations."""

        with self._lock:
            self._hud_ready = {
                str(key): bool(value)
                for key, value in status.items()
                if not str(key).startswith("buff:")
            }
            self._hud_buffs = {
                str(key).removeprefix("buff:"): bool(value)
                for key, value in status.items()
                if str(key).startswith("buff:")
            }

    def _run(self) -> None:
        next_hud_scan = 0.0
        while not self._stop_event.is_set():
            now = self._clock()
            if self._hud_supplier is not None and now >= next_hud_scan:
                try:
                    readiness = self._hud_supplier()
                except Exception:
                    readiness = {}
                self.update_hud_status(readiness)
                next_hud_scan = now + _HUD_SCAN_SECONDS

            process_id = self._process_id_supplier()
            if process_id is None:
                self._set_bridge_status("Guild Wars 2 is not running")
                self._stop_event.wait(_BHUD_RECONNECT_SECONDS)
                continue

            try:
                stream = socket.create_connection(
                    ("127.0.0.1", bhud_port_for_pid(process_id)),
                    timeout=1.0,
                )
            except OSError:
                self._set_bridge_status("ArcDPS BHud bridge unavailable")
                self._stop_event.wait(_BHUD_RECONNECT_SECONDS)
                continue

            self._set_bridge_status("ArcDPS BHud connected")
            try:
                self._consume_stream(stream, next_hud_scan)
            finally:
                stream.close()

    def _consume_stream(self, stream: socket.socket, next_hud_scan: float) -> None:
        stream.settimeout(0.15)
        buffer = bytearray()
        while not self._stop_event.is_set():
            now = self._clock()
            if self._hud_supplier is not None and now >= next_hud_scan:
                try:
                    readiness = self._hud_supplier()
                except Exception:
                    readiness = {}
                self.update_hud_status(readiness)
                next_hud_scan = now + _HUD_SCAN_SECONDS
            try:
                chunk = stream.recv(4096)
            except TimeoutError:
                continue
            except OSError:
                self._set_bridge_status("ArcDPS BHud bridge disconnected")
                return
            if not chunk:
                self._set_bridge_status("ArcDPS BHud bridge disconnected")
                return
            buffer.extend(chunk)
            while len(buffer) >= 4:
                payload_length = struct.unpack_from("<I", buffer)[0]
                if payload_length > _BHUD_MAX_FRAME_SIZE:
                    self._set_bridge_status("ArcDPS BHud sent an invalid frame")
                    return
                if len(buffer) < 4 + payload_length:
                    break
                payload = bytes(buffer[4 : 4 + payload_length])
                del buffer[: 4 + payload_length]
                try:
                    self.ingest_payload(payload)
                except BHudProtocolError:
                    self._set_bridge_status("ArcDPS BHud protocol mismatch")

    def _ingest_combat_message(self, message: ArcDpsCombatMessage) -> None:
        event = message.event
        if event is None or self._is_duplicate_event(event):
            return
        if self._event_age_seconds(event.time_ms) > _MAX_EVENT_AGE_SECONDS:
            return
        self._remember_self_agent(event.source_agent, message.source)
        self._remember_self_agent(event.destination_agent, message.destination)
        if event.statechange == _CBTS_ANIMATIONSTART and self._is_self_source(event, message):
            self._track_skill_activation(event)
        if event.statechange in {_CBTS_BUFFINITIAL, _CBTS_BUFFAPPLY}:
            self._apply_buff(event, message)
        elif event.statechange == _CBTS_BUFFCHANGE:
            self._change_buff(event, message)
        elif event.statechange == _CBTS_BUFFREMOVE_SINGLE:
            self._remove_single_buff(event, message)
        elif event.statechange == _CBTS_BUFFREMOVE_ALL and self._is_self_source(event, message):
            self._buffs.pop(event.skill_id, None)

    def _is_duplicate_event(self, event: ArcDpsCombatEvent) -> bool:
        key = (
            event.time_ms,
            event.source_agent,
            event.destination_agent,
            event.skill_id,
            event.statechange,
            event.track_id,
            event.value,
        )
        if key in self._seen_event_ids:
            return True
        self._seen_event_ids[key] = None
        self._seen_event_ids.move_to_end(key)
        while len(self._seen_event_ids) > 1_000:
            self._seen_event_ids.popitem(last=False)
        return False

    def _remember_self_agent(self, event_agent_id: int, agent: Optional[ArcDpsAgent]) -> None:
        if agent is None or not agent.is_self:
            return
        if event_agent_id:
            self._self_agent_ids.add(event_agent_id)
        if agent.agent_id:
            self._self_agent_ids.add(agent.agent_id)

    def _is_self_source(self, event: ArcDpsCombatEvent, message: ArcDpsCombatMessage) -> bool:
        return bool(
            (message.source is not None and message.source.is_self)
            or event.source_agent in self._self_agent_ids
        )

    def _is_self_destination(self, event: ArcDpsCombatEvent, message: ArcDpsCombatMessage) -> bool:
        return bool(
            (message.destination is not None and message.destination.is_self)
            or event.destination_agent in self._self_agent_ids
        )

    def _track_skill_activation(self, event: ArcDpsCombatEvent) -> None:
        if event.skill_id <= 0:
            return
        activated_at = self._arc_time_to_monotonic(event.time_ms)
        self._skill_records[event.skill_id] = _SkillRecord(
            skill_id=event.skill_id,
            activated_at=activated_at,
        )
        self._resolve_skill_metadata(event.skill_id)

    def _resolve_skill_metadata(self, skill_id: int) -> None:
        if skill_id in self._skill_lookups_in_progress:
            return
        self._skill_lookups_in_progress.add(skill_id)

        if not self._asynchronous_skill_lookup:
            try:
                metadata = self._skill_lookup(skill_id)
            except Exception:
                metadata = None
            record = self._skill_records.get(skill_id)
            if record is not None and metadata is not None:
                record.metadata = metadata
            self._skill_lookups_in_progress.discard(skill_id)
            return

        def worker() -> None:
            try:
                metadata = self._skill_lookup(skill_id)
            except Exception:
                metadata = None
            with self._lock:
                record = self._skill_records.get(skill_id)
                if record is not None and metadata is not None:
                    record.metadata = metadata
                self._skill_lookups_in_progress.discard(skill_id)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_buff(self, event: ArcDpsCombatEvent, message: ArcDpsCombatMessage) -> None:
        if event.skill_id <= 0 or not self._is_self_destination(event, message):
            return
        self._buff_names[event.skill_id] = _buff_name(event.skill_id, message.skill_name)
        duration_ms = max(event.value, 0)
        expires_at = (
            self._arc_time_to_monotonic(event.time_ms) + duration_ms / 1000
            if duration_ms > 0
            else None
        )
        stacks = self._buffs.setdefault(event.skill_id, [])
        if event.track_id:
            stacks[:] = [stack for stack in stacks if stack.track_id != event.track_id]
        stacks.append(_BuffStack(track_id=event.track_id, expires_at=expires_at))

    def _change_buff(self, event: ArcDpsCombatEvent, message: ArcDpsCombatMessage) -> None:
        if event.skill_id <= 0 or not self._is_self_destination(event, message):
            return
        stacks = self._buffs.get(event.skill_id)
        if not stacks:
            return
        duration_ms = max(event.overstack_value, 0)
        expires_at = (
            self._arc_time_to_monotonic(event.time_ms) + duration_ms / 1000
            if duration_ms > 0
            else None
        )
        for stack in reversed(stacks):
            if not event.track_id or stack.track_id == event.track_id:
                stack.expires_at = expires_at
                break

    def _remove_single_buff(
        self,
        event: ArcDpsCombatEvent,
        message: ArcDpsCombatMessage,
    ) -> None:
        if not self._is_self_source(event, message):
            return
        stacks = self._buffs.get(event.skill_id)
        if not stacks:
            return
        if event.track_id:
            stacks[:] = [stack for stack in stacks if stack.track_id != event.track_id]
        else:
            stacks.pop()
        if not stacks:
            self._buffs.pop(event.skill_id, None)

    def _arc_time_to_monotonic(self, event_time_ms: int) -> float:
        now = self._clock()
        now_ms = int(now * 1000)
        event_mod = event_time_ms & 0xFFFF_FFFF
        now_mod = now_ms & 0xFFFF_FFFF
        delta = (event_mod - now_mod) & 0xFFFF_FFFF
        if delta > 0x7FFF_FFFF:
            delta -= 0x1_0000_0000
        return now + delta / 1000

    def _event_age_seconds(self, event_time_ms: int) -> float:
        return max(0.0, self._clock() - self._arc_time_to_monotonic(event_time_ms))

    def _expire_buffs(self, now: float) -> None:
        for skill_id, stacks in list(self._buffs.items()):
            stacks[:] = [
                stack
                for stack in stacks
                if stack.expires_at is None or stack.expires_at > now
            ]
            if not stacks:
                self._buffs.pop(skill_id, None)

    def _build_skill_snapshot(self, now: float) -> list[SkillCooldown]:
        skills: dict[str, SkillCooldown] = {}
        for slot, ready in self._hud_ready.items():
            label = _SLOT_LABELS.get(slot, slot.replace("_", " "))
            skills[slot] = SkillCooldown(
                skill_id=None,
                name=label,
                slot=slot,
                ready=ready,
                remaining_seconds=0.0 if ready else None,
            )

        for record in self._skill_records.values():
            metadata = record.metadata
            slot = metadata.slot if metadata is not None else None
            key = slot or f"skill-{record.skill_id}"
            visual_ready = self._hud_ready.get(slot) if slot is not None else None
            recharge_seconds = metadata.recharge_seconds if metadata is not None else None
            remaining = (
                max(0.0, record.activated_at + recharge_seconds - now)
                if recharge_seconds is not None
                else None
            )
            ready = visual_ready if visual_ready is not None else (remaining == 0.0 if remaining is not None else None)
            if ready:
                remaining = 0.0
            skills[key] = SkillCooldown(
                skill_id=record.skill_id,
                name=metadata.name if metadata is not None else f"Skill {record.skill_id}",
                slot=slot,
                ready=ready,
                remaining_seconds=remaining,
            )
        return sorted(skills.values(), key=lambda skill: (skill.slot or "ZZZ", skill.name))

    def _build_buff_snapshot(self, now: float) -> list[ActiveBuff]:
        buffs: list[ActiveBuff] = []
        native_names: set[str] = set()
        for skill_id, stacks in self._buffs.items():
            remaining_values = [
                stack.expires_at - now
                for stack in stacks
                if stack.expires_at is not None
            ]
            remaining = max(remaining_values, default=None)
            name = self._buff_names.get(skill_id, _buff_name(skill_id, None))
            native_names.add(name.casefold())
            buffs.append(
                ActiveBuff(
                    skill_id=skill_id,
                    name=name,
                    stacks=len(stacks),
                    remaining_seconds=max(0.0, remaining) if remaining is not None else None,
                )
            )
        for name, is_active in self._hud_buffs.items():
            if is_active and name.casefold() not in native_names:
                buffs.append(
                    ActiveBuff(
                        skill_id=_KNOWN_BUFF_IDS.get(name.casefold(), 0),
                        name=name,
                        stacks=1,
                        remaining_seconds=None,
                    )
                )
        return sorted(buffs, key=lambda buff: buff.name.casefold())

    def _set_bridge_status(self, status: str) -> None:
        with self._lock:
            self._bridge_status = status


def _find_gw2_process_id() -> Optional[int]:
    try:
        process = next(
            process
            for process in psutil.process_iter(attrs=["name", "pid"])
            if (process.info.get("name") or "").lower() == "gw2-64.exe"
        )
    except StopIteration:
        return None
    return int(process.info["pid"])


def _lookup_skill_metadata(skill_id: int) -> Optional[SkillMetadata]:
    return Gw2ApiClient().get_skill_metadata([skill_id]).get(skill_id)


def _buff_name(skill_id: int, skill_name: Optional[str]) -> str:
    if skill_name and skill_name.strip() and skill_name != "0":
        return skill_name.strip()
    return _KNOWN_BUFF_NAMES.get(skill_id, f"Buff {skill_id}")