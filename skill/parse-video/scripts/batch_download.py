#!/usr/bin/env python3
"""按顺序隔离处理多条公开视频下载，单条失败不污染其他任务。"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path

import download


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="顺序批量下载公开视频")
    parser.add_argument("sources", nargs="+", help="多条分享文本或公开链接；每条作为一个参数")
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--ffprobe", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument("--isolated-home", type=Path)
    parser.add_argument("--timeout", type=int)
    return parser


def forwarded_options(args: argparse.Namespace) -> list[str]:
    values: list[str] = []
    for name in ("binary", "ffprobe", "output_dir", "temp_root", "isolated_home", "timeout"):
        value = getattr(args, name)
        if value is not None:
            values.extend([f"--{name.replace('_', '-')}", str(value)])
    return values


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = forwarded_options(args)
    results = []
    failed = 0
    for index, source in enumerate(args.sources, start=1):
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = download.main([source, *options])
        if returncode == 0:
            try:
                detail: object = json.loads(stdout.getvalue())
            except json.JSONDecodeError:
                detail = {"raw_output": stdout.getvalue()[-1200:]}
            status = "downloaded"
        else:
            failed += 1
            detail = {"error": (stderr.getvalue() or stdout.getvalue()).strip()[-1200:]}
            status = "failed"
        results.append(
            {
                "index": index,
                "source": source,
                "status": status,
                "returncode": returncode,
                "detail": detail,
            }
        )
    print(
        json.dumps(
            {
                "status": "completed" if failed == 0 else "completed_with_failures",
                "total": len(results),
                "succeeded": len(results) - failed,
                "failed": failed,
                "processing": "sequential",
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
