#!/usr/bin/env python3
"""通过固定解析器安全下载一条公开视频，再交付到桌面“下载视频”。"""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
import uuid

from process_control import executable_command, run_process
from runtime_paths import (
    SENSITIVE_ENVIRONMENT,
    resolve_runtime_paths,
    safe_child_environment,
)
from safe_names import delivery_folder_name


RUNTIME = resolve_runtime_paths()
BINARY = RUNTIME.parser_binary
OUTPUT_DIR = RUNTIME.download_root
ISOLATED_HOME = RUNTIME.isolated_home
TEMP_ROOT = RUNTIME.temp_root


def default_runtime_tool(name: str) -> Path:
    executable_name = f"{name}.exe" if RUNTIME.platform_name == "windows" else name
    bundled = RUNTIME.runtime_dir / executable_name
    discovered = shutil.which(name)
    if bundled.is_file():
        return bundled
    return Path(discovered) if discovered else bundled


FFPROBE = default_runtime_tool("ffprobe")
SENSITIVE_ENV = tuple(sorted(SENSITIVE_ENVIRONMENT))
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
PLATFORM_DOMAINS = (
    ("douyin", ("douyin.com", "iesdouyin.com")),
    ("kuaishou", ("kuaishou.com",)),
    ("xiaohongshu", ("xiaohongshu.com", "xhslink.com", "xhslink.cn")),
    ("bilibili", ("bilibili.com", "b23.tv")),
    ("weibo", ("weibo.com", "weibo.cn")),
    ("xigua", ("ixigua.com",)),
    ("qqvideo", ("v.qq.com",)),
)


def build_command(source: str, binary: Path, output_dir: Path) -> list[str]:
    return executable_command(
        binary,
        "parse",
        "--format",
        "json",
        "--download",
        "--output-dir",
        str(output_dir),
        source,
    )


def sanitized_environment(
    home: Path,
    process_temp: Path,
    *tools: Path,
) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    process_temp.mkdir(parents=True, exist_ok=True)
    return safe_child_environment(
        home,
        process_temp,
        platform_name=RUNTIME.platform_name,
        extra_path=tuple(dict.fromkeys(tool.parent for tool in tools)),
    )


def validate_runtime(
    binary: Path,
    ffprobe: Path,
    output_dir: Path,
    temp_root: Path,
) -> None:
    if not binary.is_file():
        raise RuntimeError(f"固定二进制不存在：{binary}")
    if not ffprobe.is_file():
        raise RuntimeError(f"ffprobe 不存在：{ffprobe}")
    if output_dir.exists() and not output_dir.is_dir():
        raise RuntimeError(f"输出位置不是文件夹：{output_dir}")
    if temp_root.exists() and not temp_root.is_dir():
        raise RuntimeError(f"临时位置不是文件夹：{temp_root}")


def media_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.suffix.lower() in MEDIA_SUFFIXES
        and path.stat().st_size > 0
    ]


def parser_metadata(stdout: str) -> dict[str, object]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def probe_media(
    media: Path,
    ffprobe: Path,
    env: dict[str, str],
    timeout: int,
) -> dict[str, object]:
    completed = run_process(
        executable_command(
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(media),
        ),
        env=env,
        timeout=timeout,
        platform_name=RUNTIME.platform_name,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"媒体校验失败：{media.name}：{detail[-600:]}")
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe 没有返回有效 JSON：{media.name}") from exc
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError(f"文件没有可识别的媒体流：{media.name}")
    video = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        {},
    )
    format_info = data.get("format") or {}
    duration_text = format_info.get("duration")
    duration = float(duration_text) if duration_text not in (None, "N/A") else None
    return {
        "path": str(media),
        "bytes": media.stat().st_size,
        "duration_seconds": duration,
        "width": video.get("width"),
        "height": video.get("height"),
        "container": format_info.get("format_name"),
        "stream_types": sorted(
            {
                str(stream.get("codec_type"))
                for stream in streams
                if stream.get("codec_type")
            }
        ),
    }


def platform_from_source(source: str) -> str:
    for token in source.split():
        if token.startswith("https://"):
            host = (urlparse(token.rstrip("，。；、！？,.!?;:)]}）】》\"'")).hostname or "").lower()
            for platform, domains in PLATFORM_DOMAINS:
                if any(host == domain or host.endswith(f".{domain}") for domain in domains):
                    return platform
    return "video"


def unique_destination(output_root: Path, requested_name: str) -> Path:
    candidate = output_root / requested_name
    counter = 2
    while candidate.exists():
        candidate = output_root / f"{requested_name}-{counter}"
        counter += 1
    return candidate


def deliver_media(media_dir: Path, output_root: Path, folder_name: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(output_root, folder_name)
    partial = output_root / f".parse-video-partial-{uuid.uuid4().hex}"
    try:
        shutil.copytree(media_dir, partial)
        os.replace(partial, destination)
    finally:
        if partial.exists():
            shutil.rmtree(partial)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把公开视频下载到桌面的‘下载视频’文件夹")
    parser.add_argument("source", nargs="?", help="平台分享文本或公开链接")
    parser.add_argument("--binary", type=Path, default=BINARY, help="解析器路径")
    parser.add_argument("--ffprobe", type=Path, default=FFPROBE, help="ffprobe 路径")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="最终下载根目录")
    parser.add_argument("--temp-root", type=Path, default=TEMP_ROOT, help="隔离临时目录")
    parser.add_argument("--isolated-home", type=Path, default=ISOLATED_HOME)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true", help="只检查路径和命令，不联网或下载")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    binary = args.binary.expanduser().resolve()
    ffprobe = args.ffprobe.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    temp_root = args.temp_root.expanduser().resolve()
    isolated_home = args.isolated_home.expanduser().resolve()
    try:
        validate_runtime(binary, ffprobe, output_dir, temp_root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            json.dumps(
                {
                    "binary": str(binary),
                    "ffprobe": str(ffprobe),
                    "output_dir": str(output_dir),
                    "temp_root": str(temp_root),
                    "isolated_home": str(isolated_home),
                    "platform": RUNTIME.platform_name,
                    "architecture": RUNTIME.architecture,
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

    temp_root.mkdir(parents=True, exist_ok=True)
    job_dir = Path(tempfile.mkdtemp(prefix="parse-video-", dir=str(temp_root)))
    media_dir = job_dir / "media"
    process_temp = job_dir / "process-tmp"
    media_dir.mkdir()
    try:
        child_env = sanitized_environment(
            isolated_home,
            process_temp,
            binary,
            ffprobe,
        )
        completed = run_process(
            build_command(args.source, binary, media_dir),
            env=child_env,
            timeout=args.timeout,
            platform_name=RUNTIME.platform_name,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            if detail:
                print(detail[-1200:], file=sys.stderr)
            return completed.returncode

        files = media_files(media_dir)
        if not files:
            print("下载命令没有生成非空媒体文件。", file=sys.stderr)
            return 1
        probes = [probe_media(path, ffprobe, child_env, args.timeout) for path in files]
        metadata = parser_metadata(completed.stdout)
        title = str(metadata.get("title") or files[0].stem)
        folder_name = delivery_folder_name(
            platform=platform_from_source(args.source),
            title=title,
            source_url=args.source,
            day=date.today(),
        )
        destination = deliver_media(media_dir, output_dir, folder_name)
        print(
            json.dumps(
                {
                    "status": "downloaded",
                    "output_dir": str(destination),
                    "media_files": [str(destination / path.relative_to(media_dir)) for path in files],
                    "media": [
                        {
                            **probe,
                            "path": str(
                                destination
                                / Path(str(probe["path"])).relative_to(media_dir)
                            ),
                        }
                        for probe in probes
                    ],
                    "desktop_written": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except subprocess.TimeoutExpired:
        print("下载超时，相关子进程已停止。", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
