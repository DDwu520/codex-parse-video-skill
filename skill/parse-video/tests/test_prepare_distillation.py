from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "prepare_distillation.py"
FFMPEG = Path("/opt/homebrew/bin/ffmpeg")


class PrepareDistillationCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-v1-test-")
        self.root = Path(self.temp_context.name)
        self.temp_root = self.root / "jobs"
        self.desktop = self.root / "desktop-downloads"
        self.fixture = self.root / "fixture.mp4"

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def run_cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            self.fail(
                f"CLI failed ({completed.returncode}):\nstdout={completed.stdout}\n"
                f"stderr={completed.stderr}"
            )
        return completed

    def make_video_fixture(self, duration: float = 2.0) -> None:
        subprocess.run(
            [
                str(FFMPEG),
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size=320x180:rate=10:duration={duration}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:sample_rate=16000:duration={duration}",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(self.fixture),
            ],
            check=True,
        )

    def make_fake_parser(self) -> Path:
        parser = self.root / "fake-parse-video"
        parser.write_text(
            "#!/bin/sh\n"
            "output_dir=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  if [ \"$1\" = '--output-dir' ]; then\n"
            "    shift\n"
            "    output_dir=$1\n"
            "  fi\n"
            "  shift\n"
            "done\n"
            "mkdir -p \"$output_dir\"\n"
            f"cp {shlex.quote(str(self.fixture))} \"$output_dir/video.mp4\"\n"
            "printf '%s\\n' '{\"title\":\"offline fixture\"}'\n",
            encoding="utf-8",
        )
        parser.chmod(0o755)
        return parser

    def test_dry_run_accepts_supported_platform_links_without_browser_state(self) -> None:
        cases = (
            ("douyin", "https://v.douyin.com/example/"),
            ("kuaishou", "https://v.kuaishou.com/example/"),
            ("xiaohongshu", "https://xhslink.com/example"),
            ("bilibili", "https://www.bilibili.com/video/BVexample"),
            ("weibo", "https://weibo.com/123/example"),
            ("xigua", "https://v.ixigua.com/example/"),
            ("qqvideo", "https://v.qq.com/x/page/example.html"),
        )
        for platform, url in cases:
            with self.subTest(platform=platform):
                completed = self.run_cli(
                    "prepare",
                    f"复制此链接 {url} 直接观看",
                    "--mode",
                    "understand",
                    "--dry-run",
                    "--temp-root",
                    str(self.temp_root),
                )
                data = json.loads(completed.stdout)

                self.assertEqual(data["source_url"], url)
                self.assertEqual(data["source_platform"], platform)
                self.assertEqual(data["mode"], "understand")
                self.assertFalse(data["browser_cookie_used"])
                self.assertFalse(data["browser_login_required"])
                self.assertFalse(data["desktop_written"])
                self.assertNotIn("HTTP_PROXY", data["child_environment_keys"])
                self.assertNotIn("HTTPS_PROXY", data["child_environment_keys"])

    def test_rejects_multiple_or_non_https_links(self) -> None:
        multiple = self.run_cli(
            "prepare",
            "https://v.douyin.com/a/ https://v.douyin.com/b/",
            "--mode",
            "understand",
            "--dry-run",
            check=False,
        )
        insecure = self.run_cli(
            "prepare",
            "http://v.douyin.com/a/",
            "--mode",
            "understand",
            "--dry-run",
            check=False,
        )

        self.assertEqual(multiple.returncode, 2)
        self.assertIn("一条", multiple.stderr)
        self.assertEqual(insecure.returncode, 2)
        self.assertIn("HTTPS", insecure.stderr)

    def test_rejects_unsupported_lookalike_and_login_links(self) -> None:
        unsupported = self.run_cli(
            "prepare",
            "https://notbilibili.com/video/1",
            "--mode",
            "understand",
            "--dry-run",
            check=False,
        )
        login = self.run_cli(
            "prepare",
            "https://www.bilibili.com/account/login",
            "--mode",
            "understand",
            "--dry-run",
            check=False,
        )

        self.assertEqual(unsupported.returncode, 2)
        self.assertIn("支持的平台清单", unsupported.stderr)
        self.assertEqual(login.returncode, 2)
        self.assertIn("登录或验证页面", login.stderr)

    def test_supported_public_platform_uses_unified_evidence_pipeline(self) -> None:
        self.make_video_fixture()
        parser = self.make_fake_parser()
        completed = self.run_cli(
            "prepare",
            "https://v.kuaishou.com/offline-fixture/",
            "--mode",
            "understand",
            "--asr",
            "none",
            "--temp-root",
            str(self.temp_root),
            "--desktop-output-dir",
            str(self.desktop),
            "--binary",
            str(parser),
            "--min-free-bytes",
            "0",
        )
        data = json.loads(completed.stdout)
        manifest = json.loads(
            (Path(data["evidence_dir"]) / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["source_type"], "public_platform_url")
        self.assertEqual(manifest["source_platform"], "kuaishou")
        self.assertFalse(any(Path(data["work_dir"]).rglob("*.mp4")))
        self.assertFalse(self.desktop.exists())

        self.run_cli("cleanup", "--work-dir", data["work_dir"])

    def test_supported_public_platform_distill_uses_platform_evidence_name(self) -> None:
        self.make_video_fixture()
        parser = self.make_fake_parser()
        evidence_root = self.root / "evidence"
        completed = self.run_cli(
            "prepare",
            "https://xhslink.com/offline-fixture",
            "--mode",
            "distill",
            "--asr",
            "none",
            "--temp-root",
            str(self.temp_root),
            "--evidence-root",
            str(evidence_root),
            "--desktop-output-dir",
            str(self.desktop),
            "--binary",
            str(parser),
            "--min-free-bytes",
            "0",
        )
        data = json.loads(completed.stdout)
        evidence_dir = Path(data["evidence_dir"])
        manifest = json.loads(
            (evidence_dir / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(data["status"], "candidate_only")
        self.assertTrue(evidence_dir.name.startswith("xiaohongshu--"))
        self.assertEqual(manifest["source_platform"], "xiaohongshu")
        self.assertFalse(any(evidence_dir.rglob("*.mp4")))
        self.assertFalse(any(evidence_dir.rglob("*.wav")))
        self.assertFalse(any(self.temp_root.glob("parse-video-*")))
        self.assertFalse(self.desktop.exists())

    def test_understand_mode_keeps_small_evidence_until_explicit_cleanup(self) -> None:
        self.make_video_fixture()
        completed = self.run_cli(
            "prepare",
            "--local-file",
            str(self.fixture),
            "--mode",
            "understand",
            "--asr",
            "none",
            "--quality",
            "standard",
            "--temp-root",
            str(self.temp_root),
            "--desktop-output-dir",
            str(self.desktop),
        )
        data = json.loads(completed.stdout)
        work_dir = Path(data["work_dir"])
        evidence_dir = Path(data["evidence_dir"])

        self.assertEqual(data["status"], "ready_for_review")
        self.assertTrue(work_dir.is_dir())
        self.assertTrue((evidence_dir / "manifest.json").is_file())
        self.assertTrue((evidence_dir / "frame-index.md").is_file())
        self.assertTrue(list((evidence_dir / "frames").glob("*.jpg")))
        self.assertTrue(list((evidence_dir / "contact-sheets").glob("*.jpg")))
        self.assertFalse(any(work_dir.rglob("*.mp4")))
        self.assertFalse(any(work_dir.rglob("*.wav")))
        self.assertFalse(self.desktop.exists())

        cleanup = self.run_cli("cleanup", "--work-dir", str(work_dir))
        cleanup_data = json.loads(cleanup.stdout)
        self.assertEqual(cleanup_data["status"], "cleaned")
        self.assertFalse(work_dir.exists())

    def test_failure_removes_the_job_directory(self) -> None:
        invalid = self.root / "invalid.mp4"
        invalid.write_text("not a video", encoding="utf-8")
        completed = self.run_cli(
            "prepare",
            "--local-file",
            str(invalid),
            "--mode",
            "understand",
            "--asr",
            "none",
            "--temp-root",
            str(self.temp_root),
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(any(self.temp_root.glob("parse-video-*")))

    def test_local_asr_produces_timestamped_srt_and_json(self) -> None:
        self.make_video_fixture()
        completed = self.run_cli(
            "prepare",
            "--local-file",
            str(self.fixture),
            "--mode",
            "understand",
            "--asr",
            "local",
            "--temp-root",
            str(self.temp_root),
            "--min-free-bytes",
            "0",
        )
        data = json.loads(completed.stdout)
        evidence_dir = Path(data["evidence_dir"])

        self.assertTrue((evidence_dir / "transcript.timestamped.srt").is_file())
        self.assertTrue((evidence_dir / "transcript.timestamped.json").is_file())
        manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["asr"]["status"], "completed")

        self.run_cli("cleanup", "--work-dir", data["work_dir"])

    def test_distill_mode_keeps_only_candidate_evidence(self) -> None:
        self.make_video_fixture()
        evidence_root = self.root / "evidence"
        completed = self.run_cli(
            "prepare",
            "--local-file",
            str(self.fixture),
            "--mode",
            "distill",
            "--asr",
            "none",
            "--quality",
            "high",
            "--temp-root",
            str(self.temp_root),
            "--evidence-root",
            str(evidence_root),
            "--desktop-output-dir",
            str(self.desktop),
        )
        data = json.loads(completed.stdout)
        evidence_dir = Path(data["evidence_dir"])

        self.assertEqual(data["status"], "candidate_only")
        self.assertTrue((evidence_dir / "distillation-input.md").is_file())
        self.assertTrue((evidence_dir / "manifest.json").is_file())
        self.assertFalse(any(evidence_dir.rglob("*.mp4")))
        self.assertFalse(any(evidence_dir.rglob("*.wav")))
        self.assertFalse(any(self.temp_root.glob("parse-video-*")))
        self.assertFalse(self.desktop.exists())

    def test_sigterm_cleans_the_job_directory(self) -> None:
        self.make_video_fixture()
        sleeper = self.root / "slow-ffprobe"
        sleeper.write_text(
            "#!/bin/sh\n"
            "trap 'exit 143' TERM\n"
            "sleep 30\n",
            encoding="utf-8",
        )
        sleeper.chmod(0o755)
        process = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "prepare",
                "--local-file",
                str(self.fixture),
                "--mode",
                "understand",
                "--asr",
                "none",
                "--temp-root",
                str(self.temp_root),
                "--ffprobe",
                str(sleeper),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 5
        while time.time() < deadline and not any(self.temp_root.glob("parse-video-*")):
            time.sleep(0.05)
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=5)

        self.assertEqual(process.returncode, 130)
        self.assertFalse(any(self.temp_root.glob("parse-video-*")))


if __name__ == "__main__":
    unittest.main()
