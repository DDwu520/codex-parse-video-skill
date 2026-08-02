#!/bin/sh
set -eu
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$PACKAGE_DIR/skill/parse-video/run.sh" doctor "$@"
