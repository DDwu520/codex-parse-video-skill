#!/usr/bin/env python3
"""组装自包含的 macOS 双架构候选包。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import struct
import sys
import tempfile
import zipfile


PYINSTALLER_VERSION = "6.21.0"
TARGET_CPU_TYPES = {
    "macos-arm64": 0x0100000C,
    "macos-x64": 0x01000007,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def macho_cpu_type(path: Path) -> int:
    if not path.is_file():
        raise RuntimeError(f"可执行文件不存在：{path}")
    header = path.read_bytes()[:8]
    if len(header) != 8:
        raise RuntimeError(f"不是有效的 64 位 Mach-O 文件：{path}")
    magic, cpu_type = struct.unpack("<II", header)
    if magic != 0xFEEDFACF:
        raise RuntimeError(f"不是有效的 64 位 Mach-O 文件：{path}")
    return cpu_type


def validate_architecture(path: Path, target: str) -> None:
    expected = TARGET_CPU_TYPES[target]
    actual = macho_cpu_type(path)
    if actual != expected:
        raise RuntimeError(
            f"架构不匹配：{path} 期待 {target} (0x{expected:08x})，"
            f"实际为 0x{actual:08x}"
        )


def copy_skill(source: Path, destination: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {
            name
            for name in names
            if name == "__pycache__" or name.endswith((".pyc", ".pyo"))
        }
        if Path(directory).resolve() == source.resolve():
            ignored.update({"runtime", "tests"})
        return ignored

    shutil.copytree(source, destination, ignore=ignore)


def write_manifest(root: Path, version: str, target: str) -> None:
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
        "target": target,
        "status": "candidate",
        "python_helper": {
            "builder": "PyInstaller",
            "version": PYINSTALLER_VERSION,
            "mode": "onedir",
        },
        "files": files,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_zip(source_root: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_root.parent).as_posix()
            info = zipfile.ZipInfo.from_file(path, relative)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as stream:
                output.writestr(info, stream.read())


def ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build(args: argparse.Namespace) -> Path:
    repo = Path(__file__).resolve().parents[1]
    source_skill = repo / "skill" / "parse-video"
    binary = args.binary.expanduser().resolve()
    helper_bundle = args.helper_bundle.expanduser().resolve()
    helper = helper_bundle / "parse-video-helper"
    python_license = args.python_license.expanduser().resolve()
    pyinstaller_license = args.pyinstaller_license.expanduser().resolve()
    validate_architecture(binary, args.target)
    validate_architecture(helper, args.target)
    if not helper_bundle.is_dir():
        raise RuntimeError(f"PyInstaller helper 目录不存在：{helper_bundle}")
    for name, path in (
        ("CPython 许可证", python_license),
        ("PyInstaller 许可证", pyinstaller_license),
    ):
        if not path.is_file():
            raise RuntimeError(f"{name}不存在：{path}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = f"parse-video-{args.version}-{args.target}"
    archive_output = output_dir / f"{package_name}.zip"
    if archive_output.exists():
        raise RuntimeError(f"目标压缩包已存在：{archive_output}")

    with tempfile.TemporaryDirectory(prefix="parse-video-macos-package-") as temp:
        package_root = Path(temp) / package_name
        package_root.mkdir()
        copy_skill(source_skill, package_root / "skill" / "parse-video")
        (package_root / "tools").mkdir()
        for tool in ("installer.py", "verify_manifest.py"):
            shutil.copy2(repo / "tools" / tool, package_root / "tools" / tool)
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(repo / name, package_root / name)
        licenses = package_root / "licenses"
        licenses.mkdir()
        shutil.copy2(python_license, licenses / "CPYTHON-LICENSE.txt")
        shutil.copy2(pyinstaller_license, licenses / "PYINSTALLER-COPYING.txt")
        shutil.copy2(repo / "packaging" / "README-MACOS.md", package_root / "README.md")
        for launcher in (repo / "packaging" / "macos").iterdir():
            if launcher.is_file():
                shutil.copy2(launcher, package_root / launcher.name)

        runtime = package_root / "skill" / "parse-video" / "runtime" / args.target
        runtime.mkdir(parents=True)
        shutil.copy2(binary, runtime / "parse-video")
        shutil.copytree(helper_bundle, runtime / "helper")
        for executable in (
            runtime / "parse-video",
            runtime / "helper" / "parse-video-helper",
            package_root / "skill" / "parse-video" / "run.sh",
        ):
            ensure_executable(executable)
        for launcher in package_root.glob("*.command"):
            ensure_executable(launcher)

        write_manifest(package_root, args.version, args.target)
        write_zip(package_root, archive_output)
    return archive_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建 macOS parse-video 候选包")
    parser.add_argument("--version", default="v1.0.0-rc.3")
    parser.add_argument("--target", choices=sorted(TARGET_CPU_TYPES), required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--helper-bundle", type=Path, required=True)
    parser.add_argument("--python-license", type=Path, required=True)
    parser.add_argument("--pyinstaller-license", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
