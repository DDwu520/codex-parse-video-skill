#!/usr/bin/env python3
"""通过固定 parse-video 二进制下载公开媒体到桌面固定目录。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


BINARY = Path(
    "/Users/dd/Documents/技能台/隔离项目/runtime/parse-video-cbb1c5b4/parse-video"
)
OUTPUT_DIR = Path("/Users/dd/Desktop/下载视频")
ISOLATED_HOME = Path(
    "/Users/dd/Documents/技能台/隔离项目/runtime/parse-video-cbb1c5b4/home"
)
SENSITIVE_ENV = (
    "PARSE_VIDEO_PROXY",
    "PARSE_VIDEO_USERNAME",
    "PARSE_VIDEO_PASSWORD",
)
MEDIA_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
    ".avi",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
}


def build_command(source: str) -> list[str]:
    return [
        str(BINARY),
        "parse",
        "--download",
        "--output-dir",
        str(OUTPUT_DIR),
        source,
    ]


def sanitized_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in SENSITIVE_ENV:
        env.pop(name, None)
    env["HOME"] = str(ISOLATED_HOME)
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    return env


def validate_runtime() -> None:
    if not BINARY.is_file():
        raise RuntimeError(f"固定二进制不存在：{BINARY}")
    if OUTPUT_DIR.exists() and not OUTPUT_DIR.is_dir():
        raise RuntimeError(f"输出位置不是文件夹：{OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ISOLATED_HOME.mkdir(parents=True, exist_ok=True)


def media_snapshot(output_dir: Path) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    if not output_dir.is_dir():
        return snapshot
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES:
            stat = path.stat()
            snapshot[str(path.relative_to(output_dir))] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把公开视频下载到桌面的‘下载视频’文件夹"
    )
    parser.add_argument("source", nargs="?", help="平台分享文本或公开链接")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查固定路径和命令，不联网或下载",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_runtime()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            json.dumps(
                {
                    "binary": str(BINARY),
                    "output_dir": str(OUTPUT_DIR),
                    "isolated_home": str(ISOLATED_HOME),
                    "service_started": False,
                    "sensitive_environment_removed": list(SENSITIVE_ENV),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not args.source:
        print("缺少平台分享文本或公开链接。", file=sys.stderr)
        return 2

    before = media_snapshot(OUTPUT_DIR)
    completed = subprocess.run(
        build_command(args.source),
        env=sanitized_environment(),
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode

    after = media_snapshot(OUTPUT_DIR)
    changed = {name for name, metadata in after.items() if before.get(name) != metadata}
    if not changed:
        print("下载命令没有生成或更新任何媒体文件。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
