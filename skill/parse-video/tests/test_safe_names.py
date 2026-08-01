from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class SafeNameTests(unittest.TestCase):
    def test_windows_reserved_name_and_forbidden_characters_are_safe(self) -> None:
        import safe_names

        value = safe_names.safe_component("CON: ../训练计划? * .", max_length=48)

        self.assertNotEqual(value.casefold(), "con")
        for character in '<>:"/\\|?*':
            self.assertNotIn(character, value)
        self.assertFalse(value.endswith((" ", ".")))

    def test_delivery_folder_is_bounded_and_stable(self) -> None:
        import safe_names

        name = safe_names.delivery_folder_name(
            platform="xiaohongshu",
            title="中文长标题" * 40,
            source_url="https://www.xiaohongshu.com/discovery/item/example",
            day=date(2026, 8, 2),
        )

        self.assertTrue(name.startswith("xiaohongshu-20260802-"))
        self.assertLessEqual(len(name), 120)
        self.assertRegex(name, r"-[0-9a-f]{8}$")


if __name__ == "__main__":
    unittest.main()
