#!/usr/bin/env bash
# R504 候选②: vm_run partial 归因 —— 冻结 vm_run 题集 (2 题) 上重复 n=3 臂 (同题集/同 adapter/同 AOT 二进制)
# 产出: eval/rover/r504/evidence/cand2-vmrun-n3.json —— 每臂 整题率 / 用例率 / 失败模式 / 调用数与 token
# 说明: 只跑本侧 (agent), 不跑 codex —— 本候选的问题是「R503 的 partial 是否可复现」, 不是对照。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${R504_E2_ENV:-/tmp/r504_env}
PORT=${R504_E2_PORT:-48627}
AGENT_BIN=${PROBE_AGENT_BIN:-/tmp/pub_r504/agenthost/agenthost}
ARMS=${R504_E2_ARMS:-3}
TS=$REPO/eval/rover/r504/taskset-r504-vmrun.json
OUT=$REPO/eval/rover/r504/evidence/cand2-vmrun-n3.json
log() { echo "[R504-c2] $*"; }
cd "$REPO" || exit 3
mkdir -p "$D/logs" "$D/agent" "$REPO/eval/rover/r504/evidence"
[ -f "$AGENT_BIN" ] && [ -x "$AGENT_BIN" ] || { log "[致命] 缺 agenthost 可执行文件: $AGENT_BIN"; exit 3; }

# --- 0 冻结 vm_run 题集 (若不存在则用 oracle dump; 已有则复用, 保跨臂同题) ----------
if [ ! -f "$TS" ]; then
  python3 eval/probe/run_probe.py --kind program --families vm_run --n 2 --seed 20260917 \
    --solver oracle --dump-tasks "$TS" --tag r504-vmrun-oracle \
    > "$D/logs/cand2-build.txt" 2>&1 || { log "[致命] 题集构建失败"; tail -5 "$D/logs/cand2-build.txt"; exit 3; }
fi
TSHA=$(sha256sum "$TS" | cut -d' ' -f1)
log "vm_run 题集 sha256=$(echo "$TSHA" | cut -c1-16) n=$(python3 -c "import json;d=json.load(open('$TS',encoding='utf-8'));print(len(d['tasks'] if isinstance(d,dict) else d))")"

# --- 1 adapter -----------------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
rm -rf "$D/agent/cfg"; cp -r /tmp/r455_env/agent/cfg "$D/agent/cfg"
grep -rl 48615 "$D/agent/cfg" 2>/dev/null | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
DEMO_OUT=$D/adapter setsid nohup python3 eval/rover/r455/adapter_tools.py "$PORT" \
  > "$D/logs/cand2-adapter.log" 2>&1 &
APID=$!
cleanup() {
  kill -TERM "$APID" 2>/dev/null
  for _ in $(seq 1 16); do kill -0 "$APID" 2>/dev/null || break; sleep 0.5; done
  kill -KILL "$APID" 2>/dev/null
  pgrep -af "adapter_tools.py $PORT" >/dev/null && log "[告警] adapter 残留"
}
trap cleanup EXIT
ready=0
for _ in $(seq 1 40); do
  curl -s -m 3 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ready=1; break; }
  kill -0 "$APID" 2>/dev/null || { log "[致命] adapter 退出"; tail -5 "$D/logs/cand2-adapter.log"; exit 3; }
  sleep 0.5
done
[ "$ready" = "1" ] || { log "[致命] adapter 健康检查超时"; exit 3; }

# --- 2 n 臂 --------------------------------------------------------------------
for k in $(seq 1 "$ARMS"); do
  AGENTFRAMEWORK_CONFIG="$D/agent/cfg" PROBE_AGENT_BIN="$AGENT_BIN" \
    python3 eval/probe/run_probe.py --tasks "$TS" --solver agent --tag "agent-r504vmrun-a$k" \
    > "$D/logs/cand2-arm$k.txt" 2>&1
  log "臂$k rc=$? -> $(ls -t data/probe/probe-*agent-r504vmrun-a$k*.json 2>/dev/null | head -1)"
done

# --- 3 汇总 --------------------------------------------------------------------
python3 - "$OUT" "$TSHA" "$D" "$ARMS" <<'PY'
import glob, json, os, sys
out, tsha, D, arms = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rows = []
for k in range(1, arms + 1):
    fs = sorted(glob.glob(os.path.join("data/probe", "probe-*agent-r504vmrun-a%d*.json" % k)))
    if not fs:
        rows.append({"arm": k, "missing": True}); continue
    d = json.load(open(fs[-1], encoding="utf-8-sig"))
    pt = d.get("per_task") or []
    whole = sum(1 for t in pt if t.get("mode") == "ok")
    cok = sum(int(t.get("passed") or 0) for t in pt); cn = sum(int(t.get("total") or 0) for t in pt)
    tax = {}
    for t in pt:
        tax[t.get("mode")] = tax.get(t.get("mode"), 0) + 1
    rows.append({"arm": k, "json": fs[-1], "n_tasks": len(pt), "whole_ok": whole,
                 "case_ok(passed)": cok, "case_n(total)": cn, "case_rate": (cok / cn) if cn else None,
                 "whole_rate": (whole / len(pt)) if pt else None, "taxonomy": tax})
rec = {"candidate": "R504-② vm_run partial n>=3 归因",
       "taskset": "eval/rover/r504/taskset-r504-vmrun.json", "taskset_sha256": tsha,
       "arms": rows,
       "reading": "同题集重复臂: 若每臂 whole_rate==1.0 且 case_rate==1.0 ⇒ R503 的 partial 不可复现(单次采样波动); 若某臂 partial ⇒ 带失败模式复现",
       "boundary": "n 臂=同题集重复采样, 非 3 个不同题集; 只覆盖 vm_run 族, 不覆盖其它族"}
json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"arms": [{k: r.get(k) for k in ("arm", "whole_ok", "n_tasks", "case_ok(passed)", "case_n(total)", "taxonomy")} for r in rows]}, ensure_ascii=False))
PY
log "-> $OUT"
