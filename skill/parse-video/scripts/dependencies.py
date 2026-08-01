#!/usr/bin/env python3
"""经用户明确确认后，下载并校验 Windows 媒体与本地 ASR 依赖。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import Request, urlopen
import uuid
import zipfile

from runtime_paths import resolve_runtime_paths


RUNTIME = resolve_runtime_paths()


@dataclass(frozen=True)
class Dependency:
    name: str
    url: str
    sha256: str
    bytes: int
    license: str


FFMPEG = Dependency(
    name="ffmpeg-8.0.1-essentials",
    url="https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.0.1-essentials_build.zip",
    sha256="e2aaeaa0fdbc397d4794828086424d4aaa2102cef1fb6874f6ffd29c0b88b673",
    bytes=106_000_000,
    license="GPLv3（Gyan Windows essentials build）",
)
WHISPER = Dependency(
    name="whisper.cpp-v1.9.1-windows-x64",
    url="https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip",
    sha256="7d8be46ecd31828e1eb7a2ecdd0d6b314feafd82163038ab6092594b0a063539",
    bytes=7_982_101,
    license="MIT",
)
MODEL = Dependency(
    name="whisper.cpp-ggml-base-model",
    url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    sha256="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
    bytes=147_951_465,
    license="模型来源与许可见 ggerganov/whisper.cpp 模型仓库",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def requested_dependencies(component: str) -> tuple[Dependency, ...]:
    if component == "media":
        return (FFMPEG,)
    if component == "asr":
        return (WHISPER, MODEL)
    return (FFMPEG, WHISPER, MODEL)


def plan(component: str) -> dict[str, object]:
    dependencies = requested_dependencies(component)
    return {
        "status": "plan",
        "component": component,
        "downloads": [
            {
                "name": item.name,
                "url": item.url,
                "bytes": item.bytes,
                "sha256": item.sha256,
                "license": item.license,
            }
            for item in dependencies
        ],
        "estimated_download_bytes": sum(item.bytes for item in dependencies),
        "tools_destination": str(RUNTIME.tools_dir),
        "model_destination": str(RUNTIME.models_dir / "ggml-base.bin"),
        "requires_explicit_confirmation": True,
        "writes_performed": False,
    }


def download(item: Dependency, destination: Path) -> None:
    request = Request(item.url, headers={"User-Agent": "parse-video-skill/1.0"})
    with urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    actual = sha256(destination)
    if actual != item.sha256:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"{item.name} SHA-256 不匹配：期待 {item.sha256}，实际 {actual}"
        )


def safe_extract(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            candidate = (destination / member.filename).resolve()
            if candidate != root and root not in candidate.parents:
                raise RuntimeError(f"压缩包包含越界路径：{member.filename}")
        archive.extractall(destination)


def single_match(root: Path, name: str) -> Path:
    matches = [path for path in root.rglob(name) if path.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f"{name} 数量异常：找到 {len(matches)} 个。")
    return matches[0]


def stage_existing_tools(staging: Path) -> None:
    if RUNTIME.tools_dir.is_dir():
        shutil.copytree(RUNTIME.tools_dir, staging)
    else:
        staging.mkdir()


def install_tools(component: str, downloads: dict[str, Path], work_dir: Path) -> Path:
    data_root = RUNTIME.tools_dir.parent
    data_root.mkdir(parents=True, exist_ok=True)
    staging = data_root / f".{RUNTIME.tools_dir.name}-install-{uuid.uuid4().hex}"
    stage_existing_tools(staging)
    try:
        if component in {"media", "all"}:
            extracted = work_dir / "ffmpeg"
            extracted.mkdir()
            safe_extract(downloads[FFMPEG.name], extracted)
            for name in ("ffmpeg.exe", "ffprobe.exe"):
                shutil.copy2(single_match(extracted, name), staging / name)
        if component in {"asr", "all"}:
            extracted = work_dir / "whisper"
            extracted.mkdir()
            safe_extract(downloads[WHISPER.name], extracted)
            whisper_cli = single_match(extracted, "whisper-cli.exe")
            for path in whisper_cli.parent.iterdir():
                if path.is_file() and path.suffix.casefold() in {".exe", ".dll"}:
                    shutil.copy2(path, staging / path.name)

        manifest = plan(component)
        manifest["status"] = "installed"
        manifest["writes_performed"] = True
        (staging / "dependency-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        backup = None
        if RUNTIME.tools_dir.exists():
            backup = data_root / f"{RUNTIME.tools_dir.name}-backup-{uuid.uuid4().hex[:8]}"
            os.replace(RUNTIME.tools_dir, backup)
        try:
            os.replace(staging, RUNTIME.tools_dir)
        except BaseException:
            if backup and backup.exists() and not RUNTIME.tools_dir.exists():
                os.replace(backup, RUNTIME.tools_dir)
            raise
        return backup
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def install_model(model_archive: Path) -> Path:
    RUNTIME.models_dir.mkdir(parents=True, exist_ok=True)
    destination = RUNTIME.models_dir / "ggml-base.bin"
    partial = RUNTIME.models_dir / f".ggml-base-{uuid.uuid4().hex}.partial"
    shutil.copy2(model_archive, partial)
    os.replace(partial, destination)
    return destination


def install(component: str) -> dict[str, object]:
    if RUNTIME.platform_name != "windows" or RUNTIME.architecture != "x64":
        raise RuntimeError("自动依赖安装 V1 仅支持 Windows x64。")
    dependencies = requested_dependencies(component)
    required_free = sum(item.bytes for item in dependencies) * 2 + 512 * 1024**2
    free = shutil.disk_usage(RUNTIME.codex_home.parent).free
    if free < required_free:
        raise RuntimeError(f"磁盘空间不足：至少需要 {required_free} 字节可用空间。")

    with tempfile.TemporaryDirectory(prefix="parse-video-dependencies-") as temp:
        work_dir = Path(temp)
        downloads: dict[str, Path] = {}
        for item in dependencies:
            destination = work_dir / f"{item.name}.download"
            download(item, destination)
            downloads[item.name] = destination
        backup = install_tools(component, downloads, work_dir)
        model_path = None
        if component in {"asr", "all"}:
            model_path = install_model(downloads[MODEL.name])
    return {
        "status": "installed",
        "component": component,
        "tools_destination": str(RUNTIME.tools_dir),
        "model_destination": str(model_path) if model_path else None,
        "previous_tools_backup": str(backup) if backup else None,
        "verified_sha256": True,
        "service_started": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理 parse-video 本地依赖")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "install"):
        child = subparsers.add_parser(command)
        child.add_argument("component", choices=("media", "asr", "all"), nargs="?", default="all")
        if command == "install":
            child.add_argument("--confirm-download", action="store_true")
        child.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "install" and not args.confirm_download:
        print(
            "依赖安装会联网并写入本地工具/模型目录；请先运行 plan，确认后再加 --confirm-download。",
            file=sys.stderr,
        )
        return 2
    try:
        result = plan(args.component) if args.command == "plan" else install(args.component)
    except (RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
