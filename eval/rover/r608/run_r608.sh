#!/usr/bin/env bash
# R608 · 真机臂（RF0004.1 开工：开放域识别统一出口 `{标签|abstain, 依据}` 落地）
# 单变量 = AGENTFRAMEWORK_RECOGNITION_VERDICT（T=未设/产品缺省 on · C=显式 off）；各 3 reps。
# 派生自 eval/rover/r607/run_r607.sh（结构复用）+ 逐条声明差异:
#   ① 轮号/命名空间 R607→R608；臂集合不变（T/C 各 3 reps）。
#   ② 单变量改写: 门轴开关(AGENTFRAMEWORK_GATE_REPEAT_SKIP) → 出口开关(AGENTFRAMEWORK_RECOGNITION_VERDICT)。
#   ③ fixture 逐字复用 R583 的 fixture-shapes-line1.txt（sha c98f8ab3…）+ turns-S0.txt（sha 9dc9511f…）。
#   ④ 二进制**重新构建**（JIT Release，含本轮 2 新件 + 1 打点点位）并钉 sha。
#   ⑤ 收尾复原 = 删除 data/nlp（复原为不存在），回读断言；**不使用会覆盖产物的 EXIT trap**。
# 用法: bash eval/rover/r608/run_r608.sh
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
ROOT=$REPO/eval/rover/r608
BIN=$REPO/src/agent.host/bin/Release/net10.0/agenthost
KEYS="$HOME/.agentframework/keys.env"
PREREG=$ROOT/prereg-r608.json
FIX="$REPO/eval/rover/r583/fixture-shapes-line1.txt"
TURNS="$REPO/eval/rover/r583/turns-S0.txt"
ARMTMO=900

# ── 0 先写后跑闸: 预注册机检 ──────────────────────────────────────────────────
[ -f "$PREREG" ] || { echo "[致命] 缺预注册 $PREREG"; exit 3; }
python3 - "$PREREG" <<'PY' || { echo "[致命] 预注册机检不过"; exit 3; }
import io, json, sys
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
assert d["round"] == "R608" and d["written_before_run"] is True
assert set(d["arms"]) == {"T", "C"}, sorted(d["arms"])
assert d["arms"]["C"]["env"]["AGENTFRAMEWORK_RECOGNITION_VERDICT"] == "off"
assert "AGENTFRAMEWORK_RECOGNITION_VERDICT" not in d["arms"]["T"]["env"]
assert d["arms"]["T"]["reps"] == 3 and d["arms"]["C"]["reps"] == 3
assert len(d["criteria"]) == 5 and len(d["falsification"]) == 3
ids = [c["id"] for c in d["criteria"]]
assert len(set(ids)) == 5
print("[先写后跑闸] prereg ok: arms=%s reps=3 criteria=%d falsification=%d"
      % (sorted(d["arms"]), len(d["criteria"]), len(d["falsification"])))
PY

# ── 1 前置闸: key 面 + 远端预检 ──────────────────────────────────────────────
if [ -z "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" ] && [ -f "$KEYS" ]; then set -a; . "$KEYS"; set +a; fi
if [ -z "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" ]; then
  echo "VOID: AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置 ⇒ 不起臂" > "$ROOT/gate-pre-r608.txt"; exit 4
fi
PRE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 \
  -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer ${AGENTFRAMEWORK_KEYS_DEEPSEEK}" \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-flash","messages":[{"role":"user","content":"ok"}],"max_tokens":1}' 2>/dev/null)
{
  echo "ts=$(date -Is)"
  echo "http_code=$PRE"
  echo "key_len=${#AGENTFRAMEWORK_KEYS_DEEPSEEK}"
  echo "mem_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)"
} > "$ROOT/gate-pre-r608.txt"
if [ "$PRE" != "200" ]; then
  echo "VOID: 远端预检 http=$PRE ⇒ 不起臂" >> "$ROOT/gate-pre-r608.txt"; exit 4
fi

# ── 2 起臂前状态 + fixture 前置 ──────────────────────────────────────────────
{
  echo "ts_start=$(date -Is)"
  echo "head=$(git rev-parse HEAD)"
  echo "tree_dirty=$(git status --porcelain | wc -l)"
  echo "src_dirty=$(git status --porcelain src/ | wc -l)"
  echo "bin_sha256=$(sha256sum "$BIN" | cut -d' ' -f1)"
  echo "bin_bytes=$(stat -c %s "$BIN")"
  echo "bin_mtime=$(stat -c %y "$BIN")"
  echo "host_jsonl_bytes_before=$(wc -c < data/telemetry/host.jsonl)"
  echo "nlp_dir_before=$(test -d data/nlp && echo present || echo absent)"
  echo "mem_before=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB"
} | tee "$ROOT/pre-arm-state.txt"
[ ! -d data/nlp ] || { echo "[致命] data/nlp 已存在 ⇒ 前置不成立"; exit 3; }
mkdir -p data/nlp
cp "$FIX" data/nlp/gate-shapes.txt
echo "fixture_placed=$(sha256sum data/nlp/gate-shapes.txt | cut -d' ' -f1)" >> "$ROOT/pre-arm-state.txt"
grep -q "$(cut -d' ' -f1 <<<"$(sha256sum "$FIX")")" "$ROOT/pre-arm-state.txt" \
  || { echo "[致命] fixture sha 不匹配"; exit 3; }

# ── 3 臂循环（严格串行） ─────────────────────────────────────────────────────
: > "$ROOT/arm-meta.txt"
echo "[" > "$ROOT/offsets-r608.json"
first=1
run_arm() {                     # $1=臂T/C  $2=rep  $3=变量值(unset|off)
  local arm="$1" rep="$2" val="$3" sess off start end rc
  sess="r608$(echo "$arm" | tr 'A-Z' 'a-z')$rep"
  off=$(wc -c < data/telemetry/host.jsonl)
  start=$(date +%s)
  if [ "$val" = "unset" ]; then
    { cat "$TURNS"; printf '/exit\n'; } | env -u AGENTFRAMEWORK_RECOGNITION_VERDICT timeout "$ARMTMO" "$BIN" \
        --role ./skeptic.rbin --session-id "$sess" 2>&1 \
        | head -c 4194304 > "$ROOT/arm-$arm-r$rep.out.txt"
    rc=${PIPESTATUS[1]}
  else
    { cat "$TURNS"; printf '/exit\n'; } | AGENTFRAMEWORK_RECOGNITION_VERDICT="$val" timeout "$ARMTMO" "$BIN" \
        --role ./skeptic.rbin --session-id "$sess" 2>&1 \
        | head -c 4194304 > "$ROOT/arm-$arm-r$rep.out.txt"
    rc=${PIPESTATUS[1]}
  fi
  end=$(date +%s)
  local after; after=$(wc -c < data/telemetry/host.jsonl)
  {
    echo "arm=$arm rep=$rep session=$sess var=$val rc=$rc secs=$((end-start))"
    echo "  off=$off after=$after bytes=$((after-off))"
    echo "  mem_after=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB log=$(wc -c < "$ROOT/arm-$arm-r$rep.out.txt")"
  } >> "$ROOT/arm-meta.txt"
  [ $first -eq 1 ] || printf ',\n' >> "$ROOT/offsets-r608.json"
  first=0
  printf ' {"arm":"%s","rep":%s,"session":"%s","var":"%s","rc":%s,"off":%s,"after":%s,"secs":%s}' \
    "$arm" "$rep" "$sess" "$val" "$rc" "$off" "$after" "$((end-start))" >> "$ROOT/offsets-r608.json"
  echo "ARM $arm r$rep done rc=$rc secs=$((end-start)) bytes=$((after-off))"
}
run_arm T 1 unset
run_arm C 1 off
run_arm T 2 unset
run_arm C 2 off
run_arm T 3 unset
run_arm C 3 off
printf '\n]\n' >> "$ROOT/offsets-r608.json"

# ── 4 收尾复原（无 EXIT trap；显式复原 + 回读断言） ──────────────────────────
rm -rf data/nlp
if [ -d data/nlp ]; then echo "[收尾] FAIL: data/nlp 复原失败" >> "$ROOT/arm-meta.txt"; else
  echo "[收尾] data/nlp 已复原为 absent (回读断言 OK)" >> "$ROOT/arm-meta.txt"; fi
echo "ALL_ARMS_DONE $(date -Is)" >> "$ROOT/arm-meta.txt"
python3 -c "import json,io;json.load(io.open('eval/rover/r608/offsets-r608.json'));print('[offsets] JSON ok')"
