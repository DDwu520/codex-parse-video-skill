from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "batch_download.py"


class BatchDownloadCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-batch-test-")
        self.root = Path(self.temp_context.name)

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def test_two_links_are_delivered_sequentially_to_separate_folders(self) -> None:
        parser = self.root / "fake-parser.py"
        parser.write_text(
            "import json\n"
            "from pathlib import Path\n"
            "import sys\n"
            "output = Path(sys.argv[sys.argv.index('--output-dir') + 1])\n"
            "output.mkdir(parents=True, exist_ok=True)\n"
            "source = sys.argv[-1]\n"
            "(output / 'video.mp4').write_bytes(source.encode('utf-8'))\n"
            "print(json.dumps({'title': source.rsplit('/', 1)[-1]}))\n",
            encoding="utf-8",
        )
        ffprobe = self.root / "fake-ffprobe.py"
        ffprobe.write_text(
            "print('{\"format\":{\"duration\":\"1\",\"format_name\":\"mp4\"},'"
            "'\"streams\":[{\"codec_type\":\"video\",\"width\":1,\"height\":1}]}')\n",
            encoding="utf-8",
        )
        output = self.root / "桌面" / "下载视频"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "https://weibo.com/1/first",
                "https://weibo.com/2/second",
                "--binary",
                str(parser),
                "--ffprobe",
                str(ffprobe),
                "--output-dir",
                str(output),
                "--temp-root",
                str(self.root / "jobs"),
                "--isolated-home",
                str(self.root / "home"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["succeeded"], 2)
        self.assertEqual(report["processing"], "sequential")
        deliveries = [path for path in output.iterdir() if path.is_dir()]
        self.assertEqual(len(deliveries), 2)


if __name__ == "__main__":
    unittest.main()
