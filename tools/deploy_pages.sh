#!/usr/bin/env bash
# 生成静态站并推到 gh-pages 分支。main 分支只放 markdown，产物不进 main。
#
#   ./tools/deploy_pages.sh
#
# gh-pages 是产物分支：每次覆盖式重建文件，但保留提交历史（方便回看某天线上是什么样）。
set -euo pipefail
cd "$(dirname "$0")/.."

python3 tools/build_pages.py

REMOTE=$(git remote get-url origin)
NAME=$(git config user.name  || echo Code2AI)
MAIL=$(git config user.email || echo dev@code2ai.codes)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if git clone -q --branch gh-pages --single-branch "$REMOTE" "$TMP" 2>/dev/null; then
  echo "→ 已有 gh-pages 分支，增量更新"
else
  echo "→ gh-pages 分支不存在，新建（独立历史，不含 main 的提交）"
  rm -rf "$TMP"; mkdir -p "$TMP"
  git init -q "$TMP"
  git -C "$TMP" checkout -q -b gh-pages
  git -C "$TMP" remote add origin "$REMOTE"
fi

# 先清空再拷贝：md 删掉一页时，线上对应的 html 也要跟着消失
find "$TMP" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -r _site/. "$TMP"/

cd "$TMP"
git add -A
if git diff --cached --quiet; then
  echo "✅ 内容没变化，不用推"
  exit 0
fi
git -c user.name="$NAME" -c user.email="$MAIL" \
    commit -q -m "build: 从 $(git -C "$OLDPWD" rev-parse --short HEAD 2>/dev/null || echo main) 生成静态站"
git push -q origin gh-pages
echo "✅ 已推送 gh-pages"
