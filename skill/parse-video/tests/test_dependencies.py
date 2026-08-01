from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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
        completed = self.run_cli("plan", "all", "--json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(len(report["downloads"]), 3)
        self.assertTrue(report["requires_explicit_confirmation"])
        self.assertFalse(report["writes_performed"])
        for item in report["downloads"]:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["bytes"], 0)

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
