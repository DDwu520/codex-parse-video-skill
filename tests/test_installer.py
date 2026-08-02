from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools" / "installer.py"


class InstallerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-installer-test-")
        self.root = Path(self.temp_context.name)
        self.codex_home = self.root / "自定义 Codex Home"
        self.source = self.root / "分享包" / "skill" / "parse-video"
        (self.source / "scripts").mkdir(parents=True)
        (self.source / "SKILL.md").write_text("version one", encoding="utf-8")
        (self.source / "scripts" / "parse_video.py").write_text("# v1\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def run_installer(self, *args: str, check: bool = True) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(INSTALLER), *args, "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        if check and completed.returncode != 0:
            self.fail(
                f"installer failed ({completed.returncode})\n"
                f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
        return json.loads(completed.stdout)

    def test_install_upgrade_rollback_and_uninstall_are_recoverable(self) -> None:
        installed = self.run_installer(
            "install",
            "--source",
            str(self.source),
            "--codex-home",
            str(self.codex_home),
        )
        destination = self.codex_home / "skills" / "parse-video"
        self.assertEqual(installed["status"], "installed")
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "version one")

        (self.source / "SKILL.md").write_text("version two", encoding="utf-8")
        upgraded = self.run_installer(
            "install",
            "--source",
            str(self.source),
            "--codex-home",
            str(self.codex_home),
        )
        self.assertEqual(upgraded["status"], "upgraded")
        self.assertTrue(Path(str(upgraded["backup"])).is_dir())
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "version two")

        rolled_back = self.run_installer(
            "rollback",
            "--codex-home",
            str(self.codex_home),
        )
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "version one")

        unrelated = self.root / "桌面" / "下载视频" / "keep.mp4"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b"keep")
        uninstalled = self.run_installer(
            "uninstall",
            "--codex-home",
            str(self.codex_home),
        )
        self.assertEqual(uninstalled["status"], "uninstalled")
        self.assertFalse(destination.exists())
        self.assertTrue(Path(str(uninstalled["backup"])).is_dir())
        self.assertEqual(unrelated.read_bytes(), b"keep")

    def test_dry_run_does_not_create_codex_home(self) -> None:
        report = self.run_installer(
            "install",
            "--source",
            str(self.source),
            "--codex-home",
            str(self.codex_home),
            "--dry-run",
        )

        self.assertEqual(report["status"], "dry_run")
        self.assertFalse(self.codex_home.exists())

    def test_json_output_survives_non_utf8_console_encoding(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "status",
                "--codex-home",
                str(self.codex_home),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "PYTHONIOENCODING": "cp1252",
                "PYTHONUTF8": "0",
            },
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "not_installed")

    def test_invalid_source_is_rejected_without_touching_existing_skill(self) -> None:
        destination = self.codex_home / "skills" / "parse-video"
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text("existing", encoding="utf-8")
        invalid = self.root / "invalid-source"
        invalid.mkdir()

        completed = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "install",
                "--source",
                str(invalid),
                "--codex-home",
                str(self.codex_home),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "existing")


if __name__ == "__main__":
    unittest.main()
