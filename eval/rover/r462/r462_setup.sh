#!/usr/bin/env bash
# R462 环境 v2 (判据修订后): 与 R461 逐字节同源夹具 (13 项, 含 artifacts) + 本轮 delta:
#   ① notes.md 追加一行 (含 .py 关键词 + 引用不存在的 report.md)
#   ② 新增 logic.unit (文本, 非白名单后缀 ⇒ 语言无关召回必须收进)
#   ③ 新增 blob.bin (含 NUL 的二进制 ⇒ 探针必须拒)
#   ④ 轮表 6 → 7 轮 (新增「引用上一会话 report.md」轮 ⇒ 记忆块必带该不存在的路径 ⇒ 构造陈旧引用)
#   ⑤ touch logic.unit notes.md (召回窗口 = 修改时间降序前 3 ⇒ 保证第 1 轮进窗口)
set -uo pipefail
S=/tmp/r457_env
E=/tmp/r462_env
rm -rf "$E"; mkdir -p "$E/agent/work" "$E/agent/cfg" "$E/logs"
cp -r "$S/agent/work/." "$E/agent/work/"
cp "$S/suite-turns.json" "$E/suite-turns.json"
cp -r "$S/agent/cfg/." "$E/agent/cfg/" 2>/dev/null
cd "$E/agent/work"
# ⑥ 移除运行期历史产物目录 (非夹具项; 它会被运行期写成最新 ⇒ 独占 mtime 降序前 3 召回窗口, 掩盖夹具文件)
rm -rf "$E/agent/work/data"
printf 'a.py b.py c.py d.py 共 4 个; report.md=已生成 (上一轮)\n' >> notes.md
printf 'logic.unit: 目录内 .py 文件共 4 个 (通用代码逻辑计数)\n' > logic.unit
printf '\x00.py ignored\x00binary payload\x00' > blob.bin
python3 - <<'PY'
import json, io
p = "/tmp/r462_env/suite-turns.json"
d = json.load(open(p, encoding="utf-8"))
extra = "另外, 把上一会话 report.md 的结论也一起给我"
if extra not in d["turns"]:
    d["turns"].append(extra)
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("turns:", len(d["turns"]))
PY
touch logic.unit notes.md   # ⑤ 保证进「修改时间降序前 3」召回窗口
echo "=== 夹具 ==="
ls -1 | tr '\n' ' '; echo
echo "=== 同源校验 (与 R461 13 项 md5 对照) ==="
( cd "$S/agent/work" && find . -type f -not -name 'notes.md' | sort | xargs md5sum | awk '{print $1}' | md5sum ) | sed 's/^/  r461_base: /'
( cd "$E/agent/work" && find . -type f -not -name 'notes.md' -not -name 'logic.unit' -not -name 'blob.bin' | sort | xargs md5sum | awk '{print $1}' | md5sum ) | sed 's/^/  r462_base: /'
echo "=== 本轮 delta ==="
tail -1 notes.md; tail -1 "$E/suite-turns.json"; ls -l logic.unit blob.bin | awk '{print "  " $5, $9}'

