from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "dependencies.py"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class DependencyCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_plan_discloses_sources_hashes_sizes_and_makes_no_writes(self) -> None:
        import dependencies

        with tempfile.TemporaryDirectory(prefix="parse-video-dependency-plan-") as temp:
            root = Path(temp)
            runtime = SimpleNamespace(
                platform_name="windows",
                architecture="x64",
                tools_dir=root / "tools",
                models_dir=root / "models",
            )
            with patch.object(dependencies, "RUNTIME", runtime):
                report = dependencies.plan("all")
        self.assertEqual(len(report["downloads"]), 3)
        self.assertTrue(report["requires_explicit_confirmation"])
        self.assertFalse(report["writes_performed"])
        for item in report["downloads"]:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["bytes"], 0)

    def test_macos_plan_never_offers_windows_binaries(self) -> None:
        import dependencies

        runtime = SimpleNamespace(
            platform_name="macos",
            architecture="arm64",
            tools_dir=Path("/tmp/tools"),
            models_dir=Path("/tmp/models"),
        )
        with patch.object(dependencies, "RUNTIME", runtime):
            report = dependencies.plan("all")

        self.assertEqual(report["status"], "unsupported")
        self.assertEqual(report["downloads"], [])
        self.assertFalse(report["writes_performed"])
        self.assertIn("macOS", report["message"])

    def test_install_refuses_to_download_without_explicit_confirmation(self) -> None:
        completed = self.run_cli("install", "all", "--json")

        self.assertEqual(completed.returncode, 2)
        self.assertIn("--confirm-download", completed.stderr)

    def test_zip_path_traversal_is_rejected(self) -> None:
        import dependencies

        with tempfile.TemporaryDirectory(prefix="parse-video-zip-test-") as temp:
            root = Path(temp)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../outside.txt", "blocked")
            destination = root / "extract"
            destination.mkdir()

            with self.assertRaisesRegex(RuntimeError, "越界路径"):
                dependencies.safe_extract(archive, destination)
            self.assertFalse((root / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
