from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class ProcessControlTests(unittest.TestCase):
    def test_python_helper_uses_current_interpreter_on_every_platform(self) -> None:
        import process_control

        script = Path("C:/测试工具/fake_parser.py")
        command = process_control.executable_command(script, "parse", "--help")

        self.assertEqual(command, [sys.executable, str(script), "parse", "--help"])

    def test_windows_starts_a_new_process_group(self) -> None:
        import process_control

        options = process_control.popen_group_options("windows")

        self.assertFalse(options.get("start_new_session", False))
        self.assertEqual(
            options["creationflags"],
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200),
        )

    def test_posix_starts_a_new_session(self) -> None:
        import process_control

        options = process_control.popen_group_options("macos")

        self.assertTrue(options["start_new_session"])
        self.assertNotIn("creationflags", options)


if __name__ == "__main__":
    unittest.main()
