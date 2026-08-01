from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "download.py"


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
        binary = self.root / "fake-parse-video"
        binary.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        binary.chmod(0o755)
        return binary

    def test_exit_zero_without_new_media_is_failure(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary("exit 0\n")
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"

        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
        ):
            result = module.main()

        self.assertNotEqual(result, 0)
        self.assertFalse(any(module.OUTPUT_DIR.iterdir()))

    def test_new_media_file_is_success(self) -> None:
        module = load_download_module()
        module.BINARY = self.make_fake_binary(
            "output_dir=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  if [ \"$1\" = '--output-dir' ]; then\n"
            "    shift\n"
            "    output_dir=$1\n"
            "  fi\n"
            "  shift\n"
            "done\n"
            "mkdir -p \"$output_dir\"\n"
            "printf 'video fixture' > \"$output_dir/result.mp4\"\n"
        )
        module.OUTPUT_DIR = self.root / "downloads"
        module.ISOLATED_HOME = self.root / "home"

        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT), "https://weibo.com/2803301701/RbqLbbEdK"],
        ):
            result = module.main()

        self.assertEqual(result, 0)
        self.assertTrue((module.OUTPUT_DIR / "result.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
