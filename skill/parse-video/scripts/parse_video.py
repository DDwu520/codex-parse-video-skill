#!/usr/bin/env python3
"""parse-video 下载、理解、蒸馏、清理和诊断的统一入口。"""

from __future__ import annotations

import sys

import batch_download
import dependencies
import doctor
import download
import prepare_distillation


USAGE = """用法：
  parse_video.py download <分享文本或链接> [高级选项]
  parse_video.py batch-download <链接1> <链接2> ... [高级选项]
  parse_video.py understand <分享文本或链接> [高级选项]
  parse_video.py distill <分享文本或链接> [高级选项]
  parse_video.py cleanup --work-dir <目录>
  parse_video.py doctor [--json]
  parse_video.py dependencies plan|install [media|asr|all]
"""


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return 0
    command, rest = arguments[0], arguments[1:]
    if command == "download":
        return download.main(rest)
    if command == "batch-download":
        return batch_download.main(rest)
    if command == "understand":
        return prepare_distillation.main(["prepare", *rest, "--mode", "understand"])
    if command == "distill":
        return prepare_distillation.main(["prepare", *rest, "--mode", "distill"])
    if command == "cleanup":
        return prepare_distillation.main(["cleanup", *rest])
    if command == "doctor":
        return doctor.main(rest)
    if command == "dependencies":
        return dependencies.main(rest)
    print(f"未知命令：{command}\n\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
