#!/usr/bin/env bash
# R505 首跑前负控编排: 预注册首写 → 派生的 R504 负控集 → 回填 checks_prefirstrun → R505 新增三项负控 → 预注册三态复核
# 全部本地, 不吃真机窗; 不触碰 R504 证据（只读）。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 4
D=${R505_NC_ENV:-/tmp/r505_nc}
PRE=eval/rover/r505/prereg_r505.json
log() { echo "[R505-NC] $*"; }
mkdir -p "$D/logs"

log "1/5 预注册首写 + 三态自检"
python3 eval/rover/r505/make_prereg_r505.py || { log "首写失败"; exit 3; }
python3 eval/rover/r505/make_prereg_r505.py --check || { log "首写后 --check 非 0"; exit 3; }

log "2/5 派生 nc_r505.sh（机械换命名空间）"
python3 eval/rover/r505/derive_nc_r505.py > "$D/logs/derive.json" 2>&1 || { log "派生失败"; exit 3; }

log "3/5 跑 R504 判据器负控集（R505 命名空间）"
R505_ENV="$D" bash eval/rover/r505/nc_r505.sh > "$D/logs/nc-main.txt" 2>&1; rc1=$?
log "nc_r505.sh rc=$rc1"
[ -f "$D/nc-r505.json" ] || { log "[致命] 缺 $D/nc-r505.json"; tail -20 "$D/logs/nc-main.txt"; exit 3; }

log "4/5 回填 nc 块到预注册（派生脚本 trap 会复原预注册 ⇒ 显式回填）"
python3 - "$D/nc-r505.json" "$PRE" <<'PY'
import json, sys, os
src, pre = sys.argv[1], sys.argv[2]
rec = json.load(open(src, encoding="utf-8-sig"))
d = json.load(open(pre, encoding="utf-8-sig"))
chk = d.setdefault("checks_prefirstrun", {})
for k, v in rec.items():
    if k.startswith("nc"):
        chk[k] = v
json.dump(d, open(pre, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("回填块:", sorted(k for k in chk if k.startswith("nc")))
PY

log "5/5 R505 新增负控（命名空间守卫 / 归因器 / 污染检出器）"
R505_NC_ENV="$D" bash eval/rover/r505/nc_r505_extra.sh > "$D/logs/nc-extra.txt" 2>&1; rc2=$?
log "nc_r505_extra.sh rc=$rc2"
python3 eval/rover/r505/make_prereg_r505.py --check; rc3=$?
log "预注册终检 rc=$rc3"
python3 - <<'PY'
import json, os
D = os.environ.get("R505_NC_ENV", "/tmp/r505_nc")
d = json.load(open("eval/rover/r505/prereg_r505.json", encoding="utf-8-sig"))
chk = d.get("checks_prefirstrun") or {}
print("checks_prefirstrun 块:")
for k in sorted(chk):
    v = chk[k]
    ok = v.get("pass") if isinstance(v, dict) else None
    tag = "PASS" if ok is True else ("rc=%s" % json.dumps(v.get("rc")) if isinstance(v, dict) and "rc" in v else "NOT/fmt")
    print("  %-34s %s" % (k, tag))
print("rc 记录:", {k: v.get("rc") for k, v in chk.items() if isinstance(v, dict) and "rc" in v})
PY
exit $(( rc1 != 0 || rc2 != 0 || rc3 != 0 ? 1 : 0 ))