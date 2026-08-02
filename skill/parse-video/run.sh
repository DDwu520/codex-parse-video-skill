#!/bin/sh
set -eu

SKILL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$(uname -m)" in
  arm64) TARGET="macos-arm64" ;;
  x86_64) TARGET="macos-x64" ;;
  *)
    echo "[parse-video] 不支持的 macOS 架构：$(uname -m)" >&2
    exit 2
    ;;
esac

HELPER="$SKILL_DIR/runtime/$TARGET/helper/parse-video-helper"
if [ ! -x "$HELPER" ]; then
  echo "[parse-video] 当前安装缺少 $TARGET 自包含运行助手。" >&2
  exit 2
fi

export PARSE_VIDEO_SKILL_DIR="$SKILL_DIR"
exec "$HELPER" skill "$@"
