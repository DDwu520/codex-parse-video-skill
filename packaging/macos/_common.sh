#!/bin/sh

parse_video_package_dir() {
  CDPATH= cd -- "$(dirname -- "$1")" && pwd
}

parse_video_target() {
  case "$(uname -m)" in
    arm64) printf '%s\n' "macos-arm64" ;;
    x86_64) printf '%s\n' "macos-x64" ;;
    *)
      echo "[parse-video] 不支持的 macOS 架构：$(uname -m)" >&2
      return 2
      ;;
  esac
}

parse_video_exec_helper() {
  package_dir=$1
  shift
  target=$(parse_video_target) || return $?
  helper="$package_dir/skill/parse-video/runtime/$target/helper/parse-video-helper"
  if [ ! -x "$helper" ]; then
    echo "[parse-video] 这个安装包不适用于当前电脑（需要 $target）。" >&2
    return 2
  fi
  PARSE_VIDEO_SKILL_DIR="$package_dir/skill/parse-video" \
    exec "$helper" "$@"
}
