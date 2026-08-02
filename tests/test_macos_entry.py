from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY = REPO_ROOT / "tools" / "macos_entry.py"


@unittest.skipUnless(sys.platform == "darwin", "macOS 入口测试仅在 macOS 运行。")
class MacOSEntryCliTests(unittest.TestCase):
    def test_skill_help_is_available_through_the_bundled_entry(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ENTRY), "skill", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("download", completed.stdout)
        self.assertIn("distill", completed.stdout)

    def test_install_and_verify_are_available_through_one_entry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="parse-video-macos-entry-") as temp:
            root = Path(temp)
            source = root / "source"
            (source / "scripts").mkdir(parents=True)
            (source / "SKILL.md").write_text("test", encoding="utf-8")
            (source / "scripts" / "parse_video.py").write_text("# test\n", encoding="utf-8")
            codex_home = root / "Codex Home"

            installed = subprocess.run(
                [
                    sys.executable,
                    str(ENTRY),
                    "install",
                    "--source",
                    str(source),
                    "--codex-home",
                    str(codex_home),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(json.loads(installed.stdout)["status"], "installed")

            release = root / "release"
            release.mkdir()
            payload = release / "payload.txt"
            payload.write_bytes(b"payload")
            (release / "manifest.json").write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": payload.name,
                                "bytes": 7,
                                "sha256": "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            verified = subprocess.run(
                [sys.executable, str(ENTRY), "verify", str(release), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(json.loads(verified.stdout)["status"], "verified")


if __name__ == "__main__":
    unittest.main()
