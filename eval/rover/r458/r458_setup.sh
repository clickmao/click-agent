#!/usr/bin/env bash
# R458 环境: 从 R457 夹具取**pristine 8 文件** (R455/R456/R457 同源), 两侧逐字节同。
# 只跑我方侧 (codex 基准冻结 —— 用户令: 禁任一侧多连次污染基准)。
set -uo pipefail
S=/tmp/r457_env
E=/tmp/r458_env
rm -rf "$E"; mkdir -p "$E/agent/work" "$E/codex/work" "$E/logs/adapter"
for f in a.py b.py c.py d.py notes.md x.txt y.txt z.txt; do
  cp "$S/agent/work/$f" "$E/agent/work/$f"
  cp "$S/agent/work/$f" "$E/codex/work/$f"
done
cp "$S/suite-turns.json" "$E/suite-turns.json"
mkdir -p "$E/agent/cfg"
cp -r "$S/agent/cfg/." "$E/agent/cfg/" 2>/dev/null
echo "cfg: $(ls $E/agent/cfg | tr '\n' ' ')"
echo "=== pristine 夹具 md5 (两侧逐字节同) ==="
( cd "$E/agent/work" && md5sum * | awk '{print $1}' | sort | md5sum ) | sed 's/^/  agent: /'
( cd "$E/codex/work" && md5sum * | awk '{print $1}' | sort | md5sum ) | sed 's/^/  codex: /'
echo "=== 轮输入 ==="
python3 -c "
import json;d=json.load(open('$E/suite-turns.json',encoding='utf-8'))
ts=d['turns'] if isinstance(d,dict) else d
[print('  T%d: %s'%(i+1,t.get('text',t) if isinstance(t,dict) else t)) for i,t in enumerate(ts)]"
