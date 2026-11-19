#!/bin/sh
repo="$1"; tag="$2"; n=$(echo "$repo" | tr / _)
dest="untrusted/repos100/$n"
[ -d "$dest" ] && exit 0
GIT_TERMINAL_PROMPT=0 git -c core.symlinks=false -c protocol.file.allow=never clone -q --depth 1 --branch "$tag" --single-branch "https://github.com/$repo" "$dest" >/dev/null 2>&1 || echo "FAIL $repo $tag"
