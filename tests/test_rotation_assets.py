from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()