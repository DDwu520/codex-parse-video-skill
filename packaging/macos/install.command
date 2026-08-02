#!/bin/sh
set -eu
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$PACKAGE_DIR/_common.sh"
parse_video_exec_helper "$PACKAGE_DIR" install --source "$PACKAGE_DIR/skill/parse-video" "$@"
