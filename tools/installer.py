#!/usr/bin/env python3
"""无需管理员权限的 parse-video Skill 安装、回滚和卸载工具。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import uuid


SKILL_NAME = "parse-video"


class InstallerError(RuntimeError):
    pass


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_source(source: Path) -> Path:
    if source.is_symlink():
        raise InstallerError("安装源不能是符号链接。")
    resolved = source.expanduser().resolve()
    required = (
        resolved / "SKILL.md",
        resolved / "scripts" / "parse_video.py",
    )
    if not resolved.is_dir() or not all(path.is_file() for path in required):
        raise InstallerError("安装源不是完整的 parse-video Skill。")
    return resolved


def install_paths(codex_home: Path) -> tuple[Path, Path, Path]:
    home = codex_home.expanduser().resolve()
    destination = home / "skills" / SKILL_NAME
    backups = home / "skill-backups" / SKILL_NAME
    return home, destination, backups


def backup_name(kind: str) -> str:
    return f"{timestamp()}-{kind}-{uuid.uuid4().hex[:8]}"


def install(source: Path, codex_home: Path, *, dry_run: bool) -> dict[str, object]:
    source = validate_source(source)
    home, destination, backups = install_paths(codex_home)
    if destination.is_symlink():
        raise InstallerError("现有 Skill 是符号链接，拒绝自动覆盖。")
    action = "upgraded" if destination.exists() else "installed"
    if dry_run:
        return {
            "status": "dry_run",
            "action": action,
            "source": str(source),
            "destination": str(destination),
            "codex_home": str(home),
            "writes_performed": False,
        }

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{SKILL_NAME}-install-{uuid.uuid4().hex}"
    backup: Path | None = None
    try:
        shutil.copytree(source, staging, symlinks=True)
        validate_source(staging)
        if destination.exists():
            backups.mkdir(parents=True, exist_ok=True)
            backup = backups / backup_name("upgrade")
            os.replace(destination, backup)
        try:
            os.replace(staging, destination)
        except BaseException:
            if backup and backup.exists() and not destination.exists():
                os.replace(backup, destination)
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "status": action,
        "source": str(source),
        "destination": str(destination),
        "codex_home": str(home),
        "backup": str(backup) if backup else None,
    }


def available_backups(backups: Path) -> list[Path]:
    if not backups.is_dir():
        return []
    return sorted(
        (
            path
            for path in backups.iterdir()
            if path.is_dir() and "-upgrade-" in path.name and not path.is_symlink()
        ),
        key=lambda path: path.name,
        reverse=True,
    )


def rollback(codex_home: Path, *, dry_run: bool) -> dict[str, object]:
    home, destination, backups = install_paths(codex_home)
    candidates = available_backups(backups)
    if not candidates:
        raise InstallerError("没有可回滚的旧版本。")
    selected = candidates[0]
    if destination.is_symlink():
        raise InstallerError("现有 Skill 是符号链接，拒绝自动回滚。")
    if dry_run:
        return {
            "status": "dry_run",
            "action": "rollback",
            "backup": str(selected),
            "destination": str(destination),
            "writes_performed": False,
        }

    backups.mkdir(parents=True, exist_ok=True)
    replaced: Path | None = None
    if destination.exists():
        replaced = backups / backup_name("rollback-current")
        os.replace(destination, replaced)
    try:
        os.replace(selected, destination)
    except BaseException:
        if replaced and replaced.exists() and not destination.exists():
            os.replace(replaced, destination)
        raise
    return {
        "status": "rolled_back",
        "destination": str(destination),
        "restored_from": str(selected),
        "replaced_backup": str(replaced) if replaced else None,
        "codex_home": str(home),
    }


def uninstall(codex_home: Path, *, dry_run: bool) -> dict[str, object]:
    home, destination, backups = install_paths(codex_home)
    if destination.is_symlink():
        raise InstallerError("现有 Skill 是符号链接，拒绝自动卸载。")
    if not destination.is_dir():
        raise InstallerError("parse-video Skill 尚未安装。")
    backup = backups / backup_name("uninstalled")
    if dry_run:
        return {
            "status": "dry_run",
            "action": "uninstall",
            "destination": str(destination),
            "backup": str(backup),
            "writes_performed": False,
        }
    backups.mkdir(parents=True, exist_ok=True)
    os.replace(destination, backup)
    return {
        "status": "uninstalled",
        "destination": str(destination),
        "backup": str(backup),
        "codex_home": str(home),
        "videos_or_evidence_removed": False,
    }


def status(codex_home: Path) -> dict[str, object]:
    home, destination, backups = install_paths(codex_home)
    return {
        "status": "installed" if destination.is_dir() else "not_installed",
        "destination": str(destination),
        "codex_home": str(home),
        "backup_count": len(available_backups(backups)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安装或管理 parse-video Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--source", type=Path, required=True)

    for name in ("install", "rollback", "uninstall", "status"):
        command = install_parser if name == "install" else subparsers.add_parser(name)
        command.add_argument(
            "--codex-home",
            type=Path,
            default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
        )
        if name != "status":
            command.add_argument("--dry-run", action="store_true")
        command.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    args = build_parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install(args.source, args.codex_home, dry_run=args.dry_run)
        elif args.command == "rollback":
            result = rollback(args.codex_home, dry_run=args.dry_run)
        elif args.command == "uninstall":
            result = uninstall(args.codex_home, dry_run=args.dry_run)
        else:
            result = status(args.codex_home)
    except InstallerError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
