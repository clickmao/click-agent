#!/usr/bin/env bash
# R460 环境: 从 R457/R458 夹具取 pristine 8 文件 (逐字节同源), 只跑我方侧 (codex 冻结)。
set -uo pipefail
S=/tmp/r457_env
E=/tmp/r460_env
rm -rf "$E"; mkdir -p "$E/agent/work" "$E/codex/work" "$E/logs/adapter"
for f in a.py b.py c.py d.py notes.md x.txt y.txt z.txt; do
  cp "$S/agent/work/$f" "$E/agent/work/$f"
  cp "$S/agent/work/$f" "$E/codex/work/$f"
done
cp "$S/suite-turns.json" "$E/suite-turns.json"
mkdir -p "$E/agent/cfg"
cp -r "$S/agent/cfg/." "$E/agent/cfg/" 2>/dev/null
echo "cfg: $(ls $E/agent/cfg | tr '\n' ' ')"
echo "=== pristine 夹具 md5 ==="
( cd "$E/agent/work" && md5sum * | awk '{print $1}' | sort | md5sum ) | sed 's/^/  agent: /'
( cd "$E/codex/work" && md5sum * | awk '{print $1}' | sort | md5sum ) | sed 's/^/  codex: /'
