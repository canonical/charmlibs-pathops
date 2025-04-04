#!/usr/bin/env bash
# usage: pack.sh machine|kubernetes [charmcraft args]
# e.g. pack.sh kubernetes --destructive-mode
set -xueo pipefail

CHARMDIR="$1"  # machine or kubernetes
shift 1  # we'll pass the remaining args to charmcraft pack


TMPDIR=".$CHARMDIR"
rm -rf "$TMPDIR"
cp --recursive "$CHARMDIR" "$TMPDIR"

mkdir "$TMPDIR/pathops"
cp -r ../../../../pyproject.toml "$TMPDIR/pathops/"
cp -r ../../../../src "$TMPDIR/pathops/"

cd "$TMPDIR"
uv lock  # required by uv charm plugin
charmcraft pack "$@"
cd -

mkdir -p .packed
mv "$TMPDIR"/*.charm ".packed/$CHARMDIR.charm"
rm -rf "$TMPDIR"
