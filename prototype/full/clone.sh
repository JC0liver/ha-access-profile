#!/bin/sh
# Sparse shallow clone: root files + custom_components only. Usage: clone.sh <owner/repo> [tag]
repo="$1"; tag="$2"; n=$(echo "$repo" | tr / _)
dest="untrusted/repos-full/$n"
[ -d "$dest/.git" ] && exit 0
rm -rf "$dest"
if [ -n "$tag" ]; then b="--branch $tag"; else b=""; fi
if GIT_TERMINAL_PROMPT=0 git -c core.symlinks=false -c protocol.file.allow=never clone -q --depth 1 --filter=blob:none --sparse $b --single-branch "https://github.com/$repo" "$dest" >/dev/null 2>&1 \
   && git -C "$dest" -c core.symlinks=false sparse-checkout set custom_components >/dev/null 2>&1; then
  echo "ok $repo"
else
  echo "FAIL $repo ${tag:-<default>}"
fi
