"""Guild Wars 2 API client for character and account-bank information."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import requests
from dotenv import load_dotenv

API_BASE_URL = "https://api.guildwars2.com/v2"
API_KEY_ENV_VAR = "GW2_API_KEY"
_ITEM_BATCH_SIZE = 200


class Gw2ApiError(RuntimeError):
    """Raised when Guild Wars 2 account data cannot be loaded."""


@dataclass(frozen=True)
class BankSummary:
    """The account-bank figures displayed by the helper UI."""

    total_slots: int
    occupied_slots: int
    rare_gear_items: int
    exotic_gear_items: int


def load_gw2_api_key() -> Optional[str]:
    """Load the account API key from the environment or a nearby ``.env`` file."""

    configured_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if configured_key:
        return configured_key

    for env_path in _environment_paths():
        if not env_path.is_file():
            continue
        # We only reach this point when the process has no usable key, so an
        # empty inherited variable must not hide a valid local configuration.
        load_dotenv(env_path, override=True)
        configured_key = os.getenv(API_KEY_ENV_VAR, "").strip()
        if configured_key:
            return configured_key
    return None


class Gw2ApiClient:
    """Small authenticated client for the endpoints used by the application."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._api_key = (api_key or load_gw2_api_key() or "").strip()
        self._session = session or requests.Session()

    def get_characters(self) -> list[str]:
        """Return the account character names in alphabetical order."""

        payload = self._get("characters", authenticated=True)
        if not isinstance(payload, list):
            raise Gw2ApiError("Guild Wars 2 returned an invalid character list.")
        return sorted(name for name in payload if isinstance(name, str) and name)

    def get_bank_summary(self) -> BankSummary:
        """Count occupied bank slots and rare/exotic weapon or armor items."""

        bank_payload = self._get("account/bank", authenticated=True)
        if not isinstance(bank_payload, list):
            raise Gw2ApiError("Guild Wars 2 returned an invalid bank response.")

        occupied_slots = [
            slot
            for slot in bank_payload
            if isinstance(slot, dict) and _positive_item_id(slot.get("id")) is not None
        ]
        item_details = self._get_items(
            _positive_item_id(slot.get("id")) for slot in occupied_slots
        )

        rare_gear_items = 0
        exotic_gear_items = 0
        for slot in occupied_slots:
            item_id = _positive_item_id(slot.get("id"))
            if item_id is None:
                continue
            item = item_details.get(item_id)
            if not isinstance(item, dict) or item.get("type") not in {"Weapon", "Armor"}:
                continue
            count = _positive_count(slot.get("count"))
            if item.get("rarity") == "Rare":
                rare_gear_items += count
            elif item.get("rarity") == "Exotic":
                exotic_gear_items += count

        return BankSummary(
            total_slots=len(bank_payload),
            occupied_slots=len(occupied_slots),
            rare_gear_items=rare_gear_items,
            exotic_gear_items=exotic_gear_items,
        )

    def _get_items(self, item_ids: Iterable[Optional[int]]) -> dict[int, dict[str, Any]]:
        unique_item_ids = sorted({item_id for item_id in item_ids if item_id is not None})
        items: dict[int, dict[str, Any]] = {}
        for batch in _batches(unique_item_ids, _ITEM_BATCH_SIZE):
            payload = self._get("items", params={"ids": ",".join(map(str, batch))})
            if not isinstance(payload, list):
                raise Gw2ApiError("Guild Wars 2 returned invalid item data.")
            for item in payload:
                if not isinstance(item, dict):
                    continue
                item_id = _positive_item_id(item.get("id"))
                if item_id is not None:
                    items[item_id] = item
        return items

    def _get(
        self,
        endpoint: str,
        *,
        authenticated: bool = False,
        params: Optional[dict[str, str]] = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if authenticated:
            if not self._api_key:
                raise Gw2ApiError(
                    "Set GW2_API_KEY in .env before loading Guild Wars 2 account data."
                )
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = self._session.get(
                f"{API_BASE_URL}/{endpoint}",
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 401:
                message = "Guild Wars 2 rejected GW2_API_KEY. Check the key in .env."
            elif status_code == 403:
                message = (
                    f"GW2_API_KEY is missing permission for '{endpoint}'. "
                    "Create a key with the required account and character scopes."
                )
            else:
                message = "Guild Wars 2 API request failed."
            raise Gw2ApiError(message) from exc
        except requests.RequestException as exc:
            raise Gw2ApiError("Guild Wars 2 API request failed.") from exc
        except ValueError as exc:
            raise Gw2ApiError("Guild Wars 2 API returned invalid JSON.") from exc


def _environment_paths() -> tuple[Path, ...]:
    """Return supported local locations without bundling a secret into the EXE."""

    paths = [Path.cwd() / ".env"]
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / ".env")
    else:
        paths.append(Path(__file__).resolve().parents[3] / ".env")
    return tuple(dict.fromkeys(paths))


def _batches(values: list[int], batch_size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


def _positive_item_id(value: object) -> Optional[int]:
    try:
        item_id = int(value)
    except (TypeError, ValueError):
        return None
    return item_id if item_id > 0 else None


def _positive_count(value: object) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, count)