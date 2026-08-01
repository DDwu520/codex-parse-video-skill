from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "doctor.py"


class DoctorCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-doctor-test-")
        self.root = Path(self.temp_context.name)

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def helper(self, name: str, body: str = "") -> Path:
        path = self.root / f"{name}.py"
        path.write_text(body, encoding="utf-8")
        return path

    def run_doctor(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_reports_each_capability_without_network_or_service(self) -> None:
        parser = self.helper("parser", "print('parse-video v1.0.0-rc.1')\n")
        ffmpeg = self.helper("ffmpeg")
        ffprobe = self.helper("ffprobe")
        whisper = self.helper("whisper")
        model = self.root / "ggml-base.bin"
        model.write_bytes(b"fixture")

        completed = self.run_doctor(
            "--binary",
            str(parser),
            "--ffmpeg",
            str(ffmpeg),
            "--ffprobe",
            str(ffprobe),
            "--whisper-cli",
            str(whisper),
            "--whisper-model",
            str(model),
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["capabilities"]["download_ready"])
        self.assertTrue(report["capabilities"]["understand_with_local_asr_ready"])
        self.assertTrue(report["capabilities"]["distill_with_local_asr_ready"])
        self.assertFalse(report["network_accessed"])
        self.assertFalse(report["service_started"])

    def test_missing_parser_is_a_clear_failure(self) -> None:
        missing = self.root / "missing.exe"
        completed = self.run_doctor(
            "--binary",
            str(missing),
            "--ffprobe",
            str(self.helper("ffprobe")),
            "--json",
        )

        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        self.assertFalse(report["parser"]["exists"])
        self.assertFalse(report["capabilities"]["download_ready"])


if __name__ == "__main__":
    unittest.main()
