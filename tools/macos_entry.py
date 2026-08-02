#!/usr/bin/env python3
"""macOS 自包含运行助手的单一入口。"""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skill" / "parse-video" / "scripts"
for path in (REPO_ROOT / "tools", SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import installer
import parse_video
import verify_manifest


USAGE = """用法：
  parse-video-helper skill <download|batch-download|understand|distill|doctor|dependencies> ...
  parse-video-helper install --source <Skill目录> [--codex-home <目录>]
  parse-video-helper rollback|uninstall|status [--codex-home <目录>]
  parse-video-helper verify <发布目录> [--json]
"""


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return 0
    command, rest = arguments[0], arguments[1:]
    if command == "skill":
        return parse_video.main(rest)
    if command == "verify":
        return verify_manifest.main(rest)
    if command in {"install", "rollback", "uninstall", "status"}:
        return installer.main([command, *rest])
    print(f"未知命令：{command}\n\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
