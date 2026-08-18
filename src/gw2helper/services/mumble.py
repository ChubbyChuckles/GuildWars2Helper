"""MumbleLink integration for Guild Wars 2."""

from __future__ import annotations

import ctypes
import mmap
import time
from dataclasses import dataclass
from typing import Callable, Optional


class Link(ctypes.Structure):
    _fields_ = [
        ("uiVersion", ctypes.c_uint32),
        ("uiTick", ctypes.c_ulong),
        ("fAvatarPosition", ctypes.c_float * 3),
        ("fAvatarFront", ctypes.c_float * 3),
        ("fAvatarTop", ctypes.c_float * 3),
        ("name", ctypes.c_wchar * 256),
        ("fCameraPosition", ctypes.c_float * 3),
        ("fCameraFront", ctypes.c_float * 3),
        ("fCameraTop", ctypes.c_float * 3),
        ("identity", ctypes.c_wchar * 256),
        ("context_len", ctypes.c_uint32),
    ]


class Context(ctypes.Structure):
    _fields_ = [
        ("serverAddress", ctypes.c_ubyte * 28),
        ("mapId", ctypes.c_uint32),
        ("mapType", ctypes.c_uint32),
        ("shardId", ctypes.c_uint32),
        ("instance", ctypes.c_uint32),
        ("buildId", ctypes.c_uint32),
        ("uiState", ctypes.c_uint32),
        ("compassWidth", ctypes.c_uint16),
        ("compassHeight", ctypes.c_uint16),
        ("compassRotation", ctypes.c_float),
        ("playerX", ctypes.c_float),
        ("playerY", ctypes.c_float),
        ("mapCenterX", ctypes.c_float),
        ("mapCenterY", ctypes.c_float),
        ("mapScale", ctypes.c_float),
        ("processId", ctypes.c_uint32),
        ("mountIndex", ctypes.c_uint8),
    ]


@dataclass
class MumbleLink:
    """Thin wrapper above the shared memory exposed by Guild Wars 2."""

    size_link: int = ctypes.sizeof(Link)
    size_context: int = ctypes.sizeof(Context)

    def __post_init__(self) -> None:
        discarded = 256 - self.size_context + 4096
        memfile_length = self.size_link + self.size_context + discarded
        self._memfile = mmap.mmap(
            fileno=-1, length=memfile_length, tagname="MumbleLink"
        )

    def read(self) -> tuple[Link, Context]:
        self._memfile.seek(0)
        raw_link = self._memfile.read(self.size_link)
        raw_context = self._memfile.read(self.size_context)
        link = self._unpack(Link, raw_link)
        context = self._unpack(Context, raw_context)
        return link, context

    def close(self) -> None:
        self._memfile.close()

    @staticmethod
    def _unpack(ctype: type[ctypes.Structure], buf: bytes) -> ctypes.Structure:
        cstring = ctypes.create_string_buffer(buf)
        return ctypes.cast(ctypes.pointer(cstring), ctypes.POINTER(ctype)).contents


class MumbleLinkMotionTracker:
    """Report short-lived avatar movement from successive MumbleLink samples."""

    _MIN_MOVEMENT_DISTANCE = 0.05
    _MOVEMENT_HOLD_SECONDS = 0.35

    def __init__(
        self,
        *,
        link_factory: Callable[[], MumbleLink] = MumbleLink,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._link_factory = link_factory
        self._clock = clock
        self._link: Optional[MumbleLink] = None
        self._last_position: Optional[tuple[float, float, float]] = None
        self._moving_until = 0.0

    def is_moving(self) -> bool:
        now = self._clock()
        try:
            if self._link is None:
                self._link = self._link_factory()
            link, _ = self._link.read()
        except (OSError, ValueError):
            return False

        position = tuple(float(value) for value in link.fAvatarPosition)
        if self._last_position is not None:
            distance_squared = sum(
                (current - previous) ** 2
                for current, previous in zip(position, self._last_position)
            )
            if distance_squared >= self._MIN_MOVEMENT_DISTANCE**2:
                self._moving_until = now + self._MOVEMENT_HOLD_SECONDS
        self._last_position = position
        return now < self._moving_until

    def close(self) -> None:
        if self._link is None:
            return
        self._link.close()
        self._link = None
