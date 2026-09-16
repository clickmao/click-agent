#!/usr/bin/env bash
# R504 候选⑤: 全量单测 n≥10 重复跑取证 (每次独立进程; 只读落盘, 不做任何修复)
# 产出: eval/rover/r504/evidence/cand5-unit-n10.jsonl (每行一轮) + logs
set -uo pipefail
REPO=/home/agentuser/AgentFramework
N=${R504_C5_N:-10}
OUT=$REPO/eval/rover/r504/evidence/cand5-unit-n10.jsonl
LOGD=$REPO/artifacts/r504/unit
cd "$REPO" || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
mkdir -p "$LOGD"; : > "$OUT"
for k in $(seq 1 "$N"); do
  LOG=$LOGD/unit-run$k.log
  START=$(date +%s)
  env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
    "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release \
    > "$LOG" 2>&1
  RC=$?
  END=$(date +%s)
  P=$(grep -oE "已通过[!]? *失败: *[0-9]+|Passed! *- *Failed: *[0-9]+" "$LOG" | tail -1)
  PASSED=$(grep -oE "已通过: *[0-9]+|Passed: *[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+" | tail -1)
  TOTAL=$(grep -oE "总计: *[0-9]+|Total: *[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+" | tail -1)
  FAILED=$(grep -oE "失败: *[0-9]+|Failed: *[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+" | tail -1)
  SKIP=$(grep -oE "已跳过: *[0-9]+|Skipped: *[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+" | tail -1)
  python3 - "$OUT" "$k" "$RC" "$PASSED" "$FAILED" "$TOTAL" "$SKIP" "$((END-START))" "$LOG" <<'PY'
import json, sys
out, k, rc, p, f, t, s, secs, log = sys.argv[1:10]
def nz(v):
    return int(v) if v not in ("", None) else None
rec = {"run": int(k), "rc": int(rc), "passed": nz(p), "failed": nz(f), "total": nz(t),
       "skipped": nz(s), "elapsed_s": int(secs), "log": log}
with open(out, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(json.dumps(rec, ensure_ascii=False))
PY
done
echo "[R504-c5] n=$N 完成 -> $OUT"
