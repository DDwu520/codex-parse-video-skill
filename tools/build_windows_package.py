#!/usr/bin/env python3
"""组装可复现的 Windows x64 候选包；默认不联网下载依赖。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen
import zipfile


PYTHON_VERSION = "3.13.12"
PYTHON_URL = (
    "https://www.python.org/ftp/python/3.13.12/"
    "python-3.13.12-embeddable-amd64.zip"
)
PYTHON_SHA256 = "f0b5a8e2662f51cfedefaf7cc0b8c22f05b776efa4a392042946422662e3a23c"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validated_python_archive(path: Path) -> Path:
    if not path.is_file():
        raise RuntimeError(f"Python 内嵌运行时归档不存在：{path}")
    actual = sha256(path)
    if actual != PYTHON_SHA256:
        raise RuntimeError(
            f"Python 归档 SHA-256 不匹配：期待 {PYTHON_SHA256}，实际 {actual}"
        )
    return path


def download_python(destination: Path) -> Path:
    with urlopen(PYTHON_URL, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return validated_python_archive(destination)


def copy_skill(source: Path, destination: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name == "__pycache__" or name.endswith((".pyc", ".pyo"))}
        if Path(_directory).resolve() == source.resolve():
            ignored.update({"runtime", "tests"})
        return ignored

    shutil.copytree(source, destination, ignore=ignore)


def write_manifest(root: Path, version: str) -> None:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "schema_version": "parse-video-release-v1",
        "version": version,
        "target": "windows-x64",
        "status": "candidate",
        "python": {
            "version": PYTHON_VERSION,
            "source": PYTHON_URL,
            "source_sha256": PYTHON_SHA256,
        },
        "files": files,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build(args: argparse.Namespace) -> Path:
    repo = Path(__file__).resolve().parents[1]
    source_skill = repo / "skill" / "parse-video"
    binary = args.binary.expanduser().resolve()
    if not binary.is_file() or binary.suffix.casefold() != ".exe":
        raise RuntimeError(f"Windows x64 解析器不存在：{binary}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = f"parse-video-{args.version}-windows-x64"
    archive_output = output_dir / f"{package_name}.zip"
    if archive_output.exists():
        raise RuntimeError(f"目标压缩包已存在：{archive_output}")

    with tempfile.TemporaryDirectory(prefix="parse-video-package-") as temp:
        temp_root = Path(temp)
        package_root = temp_root / package_name
        package_root.mkdir()
        copy_skill(source_skill, package_root / "skill" / "parse-video")
        (package_root / "tools").mkdir()
        shutil.copy2(repo / "tools" / "installer.py", package_root / "tools" / "installer.py")
        shutil.copy2(repo / "tools" / "verify_manifest.py", package_root / "tools" / "verify_manifest.py")
        shutil.copy2(repo / "LICENSE", package_root / "LICENSE")
        shutil.copy2(repo / "THIRD_PARTY_NOTICES.md", package_root / "THIRD_PARTY_NOTICES.md")
        shutil.copy2(repo / "packaging" / "README-WINDOWS.md", package_root / "README.md")
        for launcher in (repo / "packaging" / "windows").glob("*.cmd"):
            shutil.copy2(launcher, package_root / launcher.name)

        runtime = package_root / "skill" / "parse-video" / "runtime" / "windows-x64"
        python_dir = runtime / "python"
        python_dir.mkdir(parents=True)
        shutil.copy2(binary, runtime / "parse-video.exe")

        if args.python_archive:
            python_archive = validated_python_archive(args.python_archive.expanduser().resolve())
        elif args.download_python:
            python_archive = download_python(temp_root / "python-embed.zip")
        else:
            raise RuntimeError(
                "缺少 Python 内嵌运行时。请传 --python-archive；只有明确同意联网时才用 --download-python。"
            )
        with zipfile.ZipFile(python_archive) as archive:
            archive.extractall(python_dir)
        pth = python_dir / "python313._pth"
        pth.write_text("python313.zip\n.\n..\\..\\..\\scripts\n", encoding="utf-8")

        write_manifest(package_root, args.version)
        shutil.make_archive(
            str(archive_output.with_suffix("")),
            "zip",
            root_dir=temp_root,
            base_dir=package_name,
        )
    return archive_output


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 Windows x64 parse-video 候选包")
    parser.add_argument("--version", default="v1.0.0-rc.3")
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--python-archive", type=Path)
    parser.add_argument("--download-python", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    try:
        result = build(args)
    except RuntimeError as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
