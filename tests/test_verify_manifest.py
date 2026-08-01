from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "verify_manifest.py"


class VerifyManifestCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-manifest-test-")
        self.root = Path(self.temp_context.name)
        self.payload = self.root / "中文 文件.txt"
        self.payload.write_bytes(b"payload")
        digest = hashlib.sha256(b"payload").hexdigest()
        (self.root / "manifest.json").write_text(
            json.dumps(
                {
                    "files": [
                        {
                            "path": self.payload.name,
                            "bytes": 7,
                            "sha256": digest,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def run_verify(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_manifest_passes_and_tampering_fails(self) -> None:
        valid = self.run_verify()
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["status"], "verified")

        self.payload.write_bytes(b"changed")
        invalid = self.run_verify()
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(
            json.loads(invalid.stdout)["mismatched"],
            [self.payload.name],
        )


if __name__ == "__main__":
    unittest.main()
