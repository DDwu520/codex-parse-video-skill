#!/usr/bin/env python3
"""离线检查 parse-video 三模式所需的本地运行环境。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from process_control import executable_command, run_process
from runtime_paths import resolve_runtime_paths, safe_child_environment


RUNTIME = resolve_runtime_paths()


def default_tool(name: str) -> Path:
    executable_name = f"{name}.exe" if RUNTIME.platform_name == "windows" else name
    installed = RUNTIME.tools_dir / executable_name
    bundled = RUNTIME.runtime_dir / executable_name
    discovered = shutil.which(name)
    if installed.is_file():
        return installed
    if bundled.is_file():
        return bundled
    return Path(discovered) if discovered else installed


def default_model() -> Path:
    candidates = (
        RUNTIME.models_dir / "ggml-base.bin",
        Path.home() / ".cache" / "whisper-cpp" / "ggml-base.bin",
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nearest_existing_parent(path: Path) -> Path | None:
    current = path.expanduser().resolve()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current if current.exists() else None


def path_status(path: Path) -> dict[str, object]:
    parent = nearest_existing_parent(path)
    writable = bool(parent and parent.is_dir() and __import__("os").access(parent, __import__("os").W_OK))
    return {"path": str(path), "nearest_existing_parent": str(parent) if parent else None, "writable": writable}


def parser_version(binary: Path) -> dict[str, object]:
    if not binary.is_file():
        return {"path": str(binary), "exists": False, "version": None, "sha256": None}
    with tempfile.TemporaryDirectory(prefix="parse-video-doctor-") as temp:
        temp_path = Path(temp)
        env = safe_child_environment(
            temp_path / "home",
            temp_path / "tmp",
            platform_name=RUNTIME.platform_name,
            extra_path=(binary.parent,),
        )
        (temp_path / "home").mkdir()
        (temp_path / "tmp").mkdir()
        try:
            completed = run_process(
                executable_command(binary, "version"),
                env=env,
                timeout=10,
                platform_name=RUNTIME.platform_name,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "path": str(binary),
                "exists": True,
                "version": None,
                "sha256": sha256(binary),
                "error": str(exc),
            }
    version = (completed.stdout or completed.stderr).strip()
    return {
        "path": str(binary),
        "exists": True,
        "version": version if completed.returncode == 0 else None,
        "sha256": sha256(binary),
        "error": None if completed.returncode == 0 else version[-600:],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="离线检查 parse-video 运行条件")
    parser.add_argument("--binary", type=Path, default=RUNTIME.parser_binary)
    parser.add_argument("--ffmpeg", type=Path, default=default_tool("ffmpeg"))
    parser.add_argument("--ffprobe", type=Path, default=default_tool("ffprobe"))
    parser.add_argument("--whisper-cli", type=Path, default=default_tool("whisper-cli"))
    parser.add_argument("--whisper-model", type=Path, default=default_model())
    parser.add_argument("--json", action="store_true")
    return parser


def inspect(args: argparse.Namespace) -> dict[str, object]:
    binary = args.binary.expanduser().resolve()
    ffmpeg = args.ffmpeg.expanduser().resolve()
    ffprobe = args.ffprobe.expanduser().resolve()
    whisper = args.whisper_cli.expanduser().resolve()
    model = args.whisper_model.expanduser().resolve()
    parser = parser_version(binary)
    tools = {
        "ffmpeg": {"path": str(ffmpeg), "exists": ffmpeg.is_file()},
        "ffprobe": {"path": str(ffprobe), "exists": ffprobe.is_file()},
        "whisper_cli": {"path": str(whisper), "exists": whisper.is_file()},
        "whisper_model": {"path": str(model), "exists": model.is_file()},
    }
    download_ready = bool(parser.get("version") and tools["ffprobe"]["exists"])
    evidence_ready = bool(
        download_ready and tools["ffmpeg"]["exists"] and tools["ffprobe"]["exists"]
    )
    local_asr_ready = bool(
        evidence_ready
        and tools["whisper_cli"]["exists"]
        and tools["whisper_model"]["exists"]
    )
    return {
        "schema_version": "parse-video-doctor-v1",
        "platform": RUNTIME.platform_name,
        "architecture": RUNTIME.architecture,
        "codex_home": str(RUNTIME.codex_home),
        "parser": parser,
        "tools": tools,
        "paths": {
            "downloads": path_status(RUNTIME.download_root),
            "evidence": path_status(RUNTIME.evidence_root),
            "temporary": path_status(RUNTIME.temp_root),
        },
        "capabilities": {
            "download_ready": download_ready,
            "understand_without_asr_ready": evidence_ready,
            "understand_with_local_asr_ready": local_asr_ready,
            "distill_with_local_asr_ready": local_asr_ready,
        },
        "network_accessed": False,
        "service_started": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = inspect(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        capabilities = report["capabilities"]
        print(f"系统：{report['platform']} {report['architecture']}")
        print(f"下载：{'可用' if capabilities['download_ready'] else '缺少依赖'}")
        print(
            "理解/蒸馏（本地 ASR）："
            f"{'可用' if capabilities['understand_with_local_asr_ready'] else '缺少依赖'}"
        )
    return 0 if report["capabilities"]["download_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
