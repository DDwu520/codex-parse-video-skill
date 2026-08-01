#!/usr/bin/env python3
"""parse-video 的跨平台目录、架构和最小子进程环境。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform as platform_module
import sys
import tempfile
from typing import Mapping


WINDOWS_KNOWN_FOLDER_IDS = {
    "desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
}
SENSITIVE_ENVIRONMENT = {
    "ALL_PROXY",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "NO_PROXY",
    "PARSE_VIDEO_PASSWORD",
    "PARSE_VIDEO_PROXY",
    "PARSE_VIDEO_USERNAME",
    "all_proxy",
    "https_proxy",
    "http_proxy",
    "no_proxy",
}


@dataclass(frozen=True)
class RuntimePaths:
    platform_name: str
    architecture: str
    skill_dir: Path
    codex_home: Path
    desktop: Path
    documents: Path
    download_root: Path
    evidence_root: Path
    temp_root: Path
    runtime_dir: Path
    parser_binary: Path
    isolated_home: Path
    tools_dir: Path
    models_dir: Path


def normalize_platform(value: str | None = None) -> str:
    raw = (value or sys.platform).casefold()
    if raw in {"darwin", "mac", "macos"}:
        return "macos"
    if raw in {"win32", "windows", "cygwin", "msys"}:
        return "windows"
    raise RuntimeError(f"不支持的系统：{value or sys.platform}；V1 仅支持 macOS 和 Windows。")


def normalize_architecture(value: str | None = None) -> str:
    raw = (value or platform_module.machine()).casefold()
    if raw in {"amd64", "x86_64", "x64"}:
        return "x64"
    if raw in {"arm64", "aarch64"}:
        return "arm64"
    raise RuntimeError(f"不支持的架构：{value or platform_module.machine()}")


def windows_known_folder(name: str) -> Path:
    if name not in WINDOWS_KNOWN_FOLDER_IDS:
        raise RuntimeError(f"未知 Windows 已知文件夹：{name}")
    if os.name != "nt":
        raise RuntimeError("Windows 已知文件夹只能在 Windows 上读取。")

    import ctypes
    from ctypes import wintypes
    import uuid

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    folder_id = GUID.from_buffer_copy(
        uuid.UUID(WINDOWS_KNOWN_FOLDER_IDS[name]).bytes_le
    )
    output = ctypes.c_wchar_p()
    shell32 = ctypes.windll.shell32
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.HRESULT
    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(folder_id), 0, None, ctypes.byref(output)
    )
    if result != 0 or not output.value:
        raise RuntimeError(f"无法读取 Windows 系统{name}目录（HRESULT={result}）。")
    try:
        return Path(output.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(output)


def resolve_runtime_paths(
    *,
    platform_name: str | None = None,
    architecture: str | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    temp_dir: Path | None = None,
    known_folders: Mapping[str, Path] | None = None,
    skill_dir: Path | None = None,
) -> RuntimePaths:
    system = normalize_platform(platform_name)
    arch = normalize_architecture(architecture)
    if system == "windows" and arch != "x64":
        raise RuntimeError(f"不支持的架构：Windows V1 仅支持 x64，当前为 {arch}。")

    environment = dict(os.environ if environ is None else environ)
    user_home = (home or Path.home()).expanduser()
    root = (skill_dir or Path(__file__).resolve().parents[1]).resolve()
    codex_home = Path(environment.get("CODEX_HOME", str(user_home / ".codex"))).expanduser()

    if system == "windows":
        folders = known_folders or {
            "desktop": windows_known_folder("desktop"),
            "documents": windows_known_folder("documents"),
        }
        desktop = Path(folders["desktop"])
        documents = Path(folders["documents"])
    else:
        desktop = user_home / "Desktop"
        documents = user_home / "Documents"

    platform_arch = f"{system}-{arch}"
    runtime_dir = root / "runtime" / platform_arch
    binary_name = "parse-video.exe" if system == "windows" else "parse-video"
    temp_root = Path(temp_dir or tempfile.gettempdir()) / "codex-parse-video"
    data_root = codex_home / "parse-video"
    return RuntimePaths(
        platform_name=system,
        architecture=arch,
        skill_dir=root,
        codex_home=codex_home,
        desktop=desktop,
        documents=documents,
        download_root=desktop / "下载视频",
        evidence_root=documents / "Parse Video" / "证据包",
        temp_root=temp_root,
        runtime_dir=runtime_dir,
        parser_binary=runtime_dir / binary_name,
        isolated_home=data_root / "isolated-home",
        tools_dir=data_root / "tools" / platform_arch,
        models_dir=data_root / "models",
    )


def safe_child_environment(
    isolated_home: Path,
    process_temp: Path,
    *,
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    extra_path: tuple[Path, ...] = (),
) -> dict[str, str]:
    system = normalize_platform(platform_name)
    source = dict(os.environ if environ is None else environ)
    for name in SENSITIVE_ENVIRONMENT:
        source.pop(name, None)

    path_separator = ";" if system == "windows" else ":"
    original_path = source.get("PATH", "")
    path_parts = [str(path) for path in extra_path]
    if original_path:
        path_parts.append(original_path)

    if system == "windows":
        allowed = {
            name: source[name]
            for name in ("COMSPEC", "PATHEXT", "SystemDrive", "SystemRoot", "WINDIR")
            if source.get(name)
        }
        allowed.update(
            {
                "HOME": str(isolated_home),
                "USERPROFILE": str(isolated_home),
                "TEMP": str(process_temp),
                "TMP": str(process_temp),
                "PATH": path_separator.join(path_parts),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            }
        )
        return allowed

    return {
        "HOME": str(isolated_home),
        "TMPDIR": str(process_temp),
        "PATH": path_separator.join(path_parts),
        "LANG": source.get("LANG", "en_US.UTF-8"),
        "LC_ALL": source.get("LC_ALL", "en_US.UTF-8"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
