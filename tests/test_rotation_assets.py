from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from gw2helper.automation import tasks


class RotationAssetTests(unittest.TestCase):
    def test_skill_template_is_available_from_source_assets(self) -> None:
        template_path = Path(tasks._asset_path("skill_2.png"))

        self.assertTrue(template_path.is_file())
        self.assertEqual(template_path.parent.name, "assets")

    def test_all_rotation_templates_are_present(self) -> None:
        template_names = {
            "alacrity.png",
            "blade.png",
            "quickness.png",
            "skill_2.png",
            "skill_3.png",
            "skill_4_focus.png",
            "skill_4_sword.png",
            "skill_5_focus.png",
            "skill_5_sword.png",
            "skill_f1.png",
            "skill_f2.png",
            "skill_f3.png",
            "skill_f5.png",
            "skill_heal.png",
            "skill_illusions.png",
            "skill_ultimate.png",
            "weapon_swap.png",
        }

        missing = [
            name for name in template_names if not Path(tasks._asset_path(name)).is_file()
        ]

        self.assertEqual(missing, [])

    def test_frozen_application_resolves_templates_beside_executable(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            executable = Path(temporary_directory) / "GuildWars2Helper.exe"
            executable.touch()
            asset_directory = Path(temporary_directory) / "assets"
            asset_directory.mkdir()
            template = asset_directory / "skill_2.png"
            template.touch()
            with (
                patch.object(tasks.sys, "frozen", True, create=True),
                patch.object(tasks.sys, "executable", str(executable)),
            ):
                resolved = Path(tasks._asset_path("skill_2.png"))

        self.assertEqual(resolved, template)

    def test_captures_are_written_to_the_temp_directory(self) -> None:
        capture_path = Path(tasks._capture_path("skills.png"))

        self.assertEqual(capture_path.name, "skills.png")
        self.assertEqual(capture_path.parent.name, "GuildWars2Helper")

    def test_focus_weapon_set_is_detected_from_ready_weapon_five(self) -> None:
        screenshot = Image.new("RGB", (766, 160))

        def find_template(_hud_gray, template: str) -> list[tuple[int, int]]:
            return [(0, 0)] if template == "skill_5_focus.png" else []

        with TemporaryDirectory() as temporary_directory:
            with (
                patch.object(tasks, "take_screenshot", return_value=screenshot),
                patch.object(
                    tasks,
                    "_capture_path",
                    return_value=str(Path(temporary_directory) / "combat_hud.png"),
                ),
                patch.object(
                    tasks,
                    "_find_hud_template_locations",
                    side_effect=find_template,
                ),
                patch.object(tasks, "is_cc_bar", return_value=False),
            ):
                status = tasks.read_combat_hud_status()

        self.assertTrue(status["Weapon_5"])
        self.assertTrue(status["weapon_set:focus"])
        self.assertFalse(status["weapon_set:sword"])

    def test_illusions_utility_readiness_is_reported(self) -> None:
        screenshot = Image.new("RGB", (766, 160))

        def find_template(_hud_gray, template: str) -> list[tuple[int, int]]:
            return [(0, 0)] if template == "skill_illusions.png" else []

        with TemporaryDirectory() as temporary_directory:
            with (
                patch.object(tasks, "take_screenshot", return_value=screenshot),
                patch.object(
                    tasks,
                    "_capture_path",
                    return_value=str(Path(temporary_directory) / "combat_hud.png"),
                ),
                patch.object(
                    tasks,
                    "_find_hud_template_locations",
                    side_effect=find_template,
                ),
                patch.object(tasks, "is_cc_bar", return_value=False),
            ):
                status = tasks.read_combat_hud_status()

        self.assertTrue(status["Utility_Illusions"])


if __name__ == "__main__":
    unittest.main()