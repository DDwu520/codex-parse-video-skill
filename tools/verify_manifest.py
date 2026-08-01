#!/usr/bin/env python3
"""离线核对发布目录中的文件集合、大小与 SHA-256。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root: Path) -> dict[str, object]:
    root = root.expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("发布目录缺少 manifest.json。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {str(item["path"]): item for item in manifest.get("files", [])}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    mismatched = []
    for relative in sorted(set(expected) & actual):
        path = root / relative
        item = expected[relative]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            mismatched.append(relative)
    return {
        "status": "verified" if not (missing or unexpected or mismatched) else "failed",
        "root": str(root),
        "checked_files": len(expected),
        "missing": missing,
        "unexpected": unexpected,
        "mismatched": mismatched,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核对 parse-video 发布清单")
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.root)
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {result['checked_files']} files")
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
