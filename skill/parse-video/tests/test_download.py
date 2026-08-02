from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from io import StringIO


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "download.py"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_download_module():
    spec = importlib.util.spec_from_file_location("parse_video_download", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 download.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DownloadWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-download-test-")
        self.root = Path(self.temp_context.name)

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def make_fake_binary(self, body: str) -> Path:
        binary = self.root / "fake-parse-video.py"
        binary.write_text(body, encoding="utf-8")
        return binary

    def make_fake_ffprobe(self, *, valid: bool = True) -> Path:
        tool = self.root / "fake-ffprobe.py"
        if valid:
            tool.write_text(
                "import json\n"
                "print(json.dumps({"
                "'format': {'duration': '12.5', 'format_name': 'mov,mp4'}, "
                "'streams': [{'codec_type': 'video', 'width': 720, 'height': 1280}]}))\n",
                encoding="utf-8",
            )
        else:
            tool.write_text("raise SystemExit(3)\n", encoding="utf-8")
        return tool

    def test_exit_zero_without_new_media_is_failure(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary("raise SystemExit(0)\n")
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"

        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
        ):
            result = module.main()

        self.assertNotEqual(result, 0)
        self.assertFalse(module.OUTPUT_DIR.exists())

    def test_new_media_file_is_success(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary(
            "import json\n"
            "from pathlib import Path\n"
            "import sys\n"
            "output_dir = Path(sys.argv[sys.argv.index('--output-dir') + 1])\n"
            "output_dir.mkdir(parents=True, exist_ok=True)\n"
            "(output_dir / 'result.mp4').write_bytes(b'video fixture')\n"
            "print(json.dumps({'title': 'CON: ../训练计划?'}, ensure_ascii=False))\n"
        )
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"
        module.TEMP_ROOT = self.root / "jobs"
        module.FFPROBE = self.make_fake_ffprobe()

        captured = StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
            ),
            mock.patch("sys.stdout", captured),
        ):
            result = module.main()

        self.assertEqual(result, 0)
        deliveries = list(module.OUTPUT_DIR.iterdir())
        self.assertEqual(len(deliveries), 1)
        self.assertTrue(deliveries[0].is_dir())
        self.assertTrue((deliveries[0] / "result.mp4").is_file())
        self.assertNotIn("CON", deliveries[0].name.upper().split("-"))
        self.assertFalse(any(module.TEMP_ROOT.glob("parse-video-*")))
        data = __import__("json").loads(captured.getvalue())
        self.assertEqual(data["media"][0]["duration_seconds"], 12.5)
        self.assertEqual(data["media"][0]["width"], 720)
        self.assertEqual(data["media"][0]["height"], 1280)

    def test_invalid_media_probe_does_not_deliver_files(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary(
            "from pathlib import Path\n"
            "import sys\n"
            "output_dir = Path(sys.argv[sys.argv.index('--output-dir') + 1])\n"
            "output_dir.mkdir(parents=True, exist_ok=True)\n"
            "(output_dir / 'result.mp4').write_bytes(b'not media')\n"
            "print('{}')\n"
        )
        module.FFPROBE = self.make_fake_ffprobe(valid=False)
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"
        module.TEMP_ROOT = self.root / "jobs"

        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
        ):
            result = module.main()

        self.assertNotEqual(result, 0)
        self.assertFalse(module.OUTPUT_DIR.exists())
        self.assertFalse(any(module.TEMP_ROOT.glob("parse-video-*")))

    def test_failed_download_does_not_leave_desktop_or_temp_files(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary(
            "from pathlib import Path\n"
            "import sys\n"
            "output_dir = Path(sys.argv[sys.argv.index('--output-dir') + 1])\n"
            "output_dir.mkdir(parents=True, exist_ok=True)\n"
            "(output_dir / 'partial.mp4').write_bytes(b'partial')\n"
            "raise SystemExit(7)\n"
        )
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"
        module.TEMP_ROOT = self.root / "jobs"
        module.FFPROBE = self.make_fake_ffprobe()

        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
        ):
            result = module.main()

        self.assertEqual(result, 7)
        self.assertFalse(module.OUTPUT_DIR.exists())
        self.assertFalse(any(module.TEMP_ROOT.glob("parse-video-*")))

    def test_timeout_stops_job_and_cleans_temp_files(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary("import time\ntime.sleep(30)\n")
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"
        module.TEMP_ROOT = self.root / "jobs"
        module.FFPROBE = self.make_fake_ffprobe()

        with mock.patch.object(
            sys,
            "argv",
            [
                str(SCRIPT),
                "https://weibo.com/2803301701/RbqLbbEdK",
                "--timeout",
                "1",
            ],
        ):
            result = module.main()

        self.assertEqual(result, 1)
        self.assertFalse(module.OUTPUT_DIR.exists())
        self.assertFalse(any(module.TEMP_ROOT.glob("parse-video-*")))


if __name__ == "__main__":
    unittest.main()
