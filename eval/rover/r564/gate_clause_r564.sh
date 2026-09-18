#!/usr/bin/env bash
# R564 候选③ driver — 起手闸振幅余量条款**按上一轮实测振幅派生**行使 (零产品改动 / 零新逻辑进闸)。
#
# 条款: 起手读数 >= GATE_MB(2650) + max(60, 上一轮运行中实测振幅) ∧ 起手前样本极差 <= 50MB
#        ∧ 连续 2 次 PASS ∧ blockers 空;  行使方式 = 既有闸 `--gate-mb $REQ`。
# 成对控制: 正控(空闲, 必 PASS) + 负控(真实内存占用, 必 GATE_BLOCKED)
#           + **判别力成对控制**(同一内存态 2680~2689 下, 门槛 2650 判 PASS / 门槛 2714 判 BLOCKED)。
#
# 用法: bash eval/rover/r564/gate_clause_r564.sh [OUT_DIR]
#   OUT_DIR 缺省 eval/rover/r564; 重放请在**新命名空间**下跑 (不覆盖首跑读数)。
set -u
REPO="/home/agentuser/AgentFramework"
cd "$REPO" || exit 3
OUT="${1:-$REPO/eval/rover/r564}"
D=/tmp/r564
mkdir -p "$D/logs" "$OUT"
PREV_SWING="${PREV_SWING:-64}"          # R563 gate-postcheck-r563.json swing_mb (上一轮运行中实测振幅)
GATE_MB_BASE=2650
HOG_PID=""

cleanup() { [ -n "$HOG_PID" ] && kill "$HOG_PID" 2>/dev/null; return 0; }
trap cleanup EXIT

# --- 起手前 3 次采样 (间隔 5s) ---
rm -f "$D/logs/pre-samples-$PREV_SWING.jsonl"
for _ in 1 2 3; do
  python3 "$REPO/eval/rover/r563/mem_sample_once.py" "$D/logs/pre-samples-$PREV_SWING.jsonl"
  sleep 5
done

# --- 派生 (margin 由上一轮实测振幅来) ---
python3 "$REPO/eval/rover/r563/gate_margin_r563.py" --derive \
  --samples "$D/logs/pre-samples-$PREV_SWING.jsonl" --prev-swing-mb "$PREV_SWING" \
  --embed-selftest --out "$OUT/gate-margin-r564.json" || { echo "DERIVE_RC=$?"; exit 2; }
REQ=$(python3 -c "import json,sys;print(int(json.load(open('$OUT/gate-margin-r564.json'))['required_mb']))")
echo "REQ=$REQ (expect $((GATE_MB_BASE + PREV_SWING)))"

# --- 正控: 连续 2 次 (真机, 既有闸) ---
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R564 --gate-mb "$REQ" \
    --out "$OUT/gate-pc-$i.json" > "$D/logs/gate-pc-$i.txt" 2>&1
  echo "PC$i_RC=$?"
done

# --- 负控 1: 400MB 真实占用 ---
python3 -u "$D/hog.py" 400 > "$D/logs/hog400.log" 2>&1 &
HOG_PID=$!
sleep 6
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R564 --gate-mb "$REQ" \
  --settle-max 8 --out "$OUT/gate-nc-hog.json" > "$D/logs/gate-nc-hog.txt" 2>&1
echo "NC_HOG_RC=$?"
kill "$HOG_PID" 2>/dev/null; wait "$HOG_PID" 2>/dev/null; HOG_PID=""
sleep 3

# --- 判别力成对控制: 调谐占用到 2680~2689 (高于 2650 / 低于 2714) ---
python3 -u "$D/hog_tuned.py" 2690 > "$D/logs/hog-tuned.log" 2>&1 &
HOG_PID=$!
sleep 8
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R564 --gate-mb $GATE_MB_BASE \
  --settle-max 8 --out "$OUT/gate-disc-base2650.json" > "$D/logs/gate-disc-base2650.txt" 2>&1
echo "DISC_BASE_RC=$?"
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R564 --gate-mb "$REQ" \
  --settle-max 8 --out "$OUT/gate-disc-clause2714.json" > "$D/logs/gate-disc-clause2714.txt" 2>&1
echo "DISC_CLAUSE_RC=$?"
kill "$HOG_PID" 2>/dev/null; wait "$HOG_PID" 2>/dev/null; HOG_PID=""
sleep 3
grep MemAvailable /proc/meminfo

python3 - "$OUT" <<'PY'
import json, sys, os
o = sys.argv[1]
rows = []
for f in ("gate-pc-1", "gate-pc-2", "gate-nc-hog", "gate-disc-base2650", "gate-disc-clause2714"):
    p = os.path.join(o, f + ".json")
    if os.path.isfile(p):
        r = json.load(open(p, encoding="utf-8"))
        rows.append({"file": f, "verdict": r["verdict"], "mem_mb": r["mem_available_mb"],
                     "gate_mb": r["gate_mb"], "causes": r.get("blocker_causes", [])})
print(json.dumps({"out": o, "rows": rows}, ensure_ascii=False, indent=1))
PY
