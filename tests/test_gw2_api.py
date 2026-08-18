from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from gw2helper.automation import tasks
from gw2helper.services import gw2_api


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _Session:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> _Response:
        self.requests.append({"url": url, **kwargs})
        if url.endswith("/account/bank"):
            return _Response(
                [
                    {"id": 1, "count": 2},
                    None,
                    {"id": 2, "count": 1},
                    {"id": 3, "count": 1},
                    {"id": 4, "count": 9},
                ]
            )
        if url.endswith("/items"):
            return _Response(
                [
                    {"id": 1, "type": "Weapon", "rarity": "Rare"},
                    {"id": 2, "type": "Armor", "rarity": "Exotic"},
                    {"id": 3, "type": "Trinket", "rarity": "Rare"},
                    {"id": 4, "type": "Weapon", "rarity": "Exotic"},
                ]
            )
        return _Response(["Zojja", "Caithe"])


class Gw2ApiTests(unittest.TestCase):
    def test_bank_summary_counts_occupied_slots_and_gear_quantities(self) -> None:
        session = _Session()
        client = gw2_api.Gw2ApiClient(api_key="test-key", session=session)

        summary = client.get_bank_summary()

        self.assertEqual(summary.total_slots, 5)
        self.assertEqual(summary.occupied_slots, 4)
        self.assertEqual(summary.rare_gear_items, 2)
        self.assertEqual(summary.exotic_gear_items, 10)
        self.assertEqual(
            session.requests[0]["headers"],
            {"Authorization": "Bearer test-key"},
        )
        self.assertEqual(session.requests[1]["params"], {"ids": "1,2,3,4"})

    def test_character_list_uses_the_authenticated_api_client(self) -> None:
        session = _Session()
        client = gw2_api.Gw2ApiClient(api_key="test-key", session=session)

        characters = client.get_characters()

        self.assertEqual(characters, ["Caithe", "Zojja"])
        self.assertEqual(
            session.requests[0]["headers"],
            {"Authorization": "Bearer test-key"},
        )

    def test_api_key_loads_from_dotenv_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            env_path = Path(temporary_directory) / ".env"
            env_path.write_text("GW2_API_KEY=test-from-dotenv\n", encoding="utf-8")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(gw2_api, "_environment_paths", return_value=(env_path,)),
            ):
                self.assertEqual(gw2_api.load_gw2_api_key(), "test-from-dotenv")

    def test_missing_key_has_a_clear_error(self) -> None:
        client = gw2_api.Gw2ApiClient(api_key="", session=_Session())

        with patch.object(gw2_api, "load_gw2_api_key", return_value=None):
            client = gw2_api.Gw2ApiClient(api_key="", session=_Session())
        with self.assertRaisesRegex(gw2_api.Gw2ApiError, "GW2_API_KEY"):
            client.get_bank_summary()

    def test_task_character_list_uses_the_dotenv_backed_client(self) -> None:
        client = unittest.mock.Mock()
        client.get_characters.return_value = ["Caithe", "Zojja"]

        with patch.object(tasks, "Gw2ApiClient", return_value=client):
            characters = tasks.get_character_list()

        self.assertEqual(characters, ["Caithe", "Zojja"])
        client.get_characters.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()