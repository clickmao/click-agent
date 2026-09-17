#!/usr/bin/env bash
# R544 起臂前**机制接线冒烟** (真机, 2 跑次): 产物侧公开用例回放是否真在 CLI 路径上生效。
#
# 为什么单独做: 整轮 7 臂 ≈ 30 分钟; 若探针在真机路径上没接线(有代码行 ≠ 生效), 全程白跑。
# 断言(fail-closed):
#   ≥1 跑次: transcript.json 有 "public_probe_ran": 1 ∧ reply 有 R1_PUBLIC_PROBE 标记 ⇒ 机制启用;
#   ≥1 跑次(负控, 开关 unset): transcript.json **不得**含 public_probe 字段 ⇒ 机制真缺席, 默认关零行为变化。
# 注: 探针成败(0 或 >0)不作断言 —— 那是被测模型的能力读数, 不是接线读数。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r544
S=$R/smoke-probe
BIN=${R544_AGENT_BIN:-/tmp/pub_r544/agenthost}
[ -e "$S" ] && { echo "[致命] $S 已存在(禁覆盖)"; exit 4; }
[ -x "$BIN" ] || { echo "[致命] 缺二进制 $BIN"; exit 3; }
set -a; . "$REPO/.env.local"; set +a
mkdir -p "$S"

python3 - "$S/task.txt" > "$S/task-build.txt" 2>&1 <<'PY'
import io, sys
task = (
 "用 Python 3 写一个多文件包 `sols/`（入口 `python3 -m sols <case_id>`，`<case_id>` 取 alpha）。\n\n"
 "### 游戏 `alpha`\n输入:\n7\n期望输出:\n14\n\n"
 "请把完整程序放在一个 ```python 围栏代码块内。\n")
io.open(sys.argv[1], "w", encoding="utf-8").write(task)
print("task_chars=%d" % len(task))
PY
cat "$S/task.txt"

for SW in on off; do
  mkdir -p "$S/$SW/work"
  if [ "$SW" = "on" ]; then
    env -u AGENTFRAMEWORK_R1_ROLE_FILE "AGENTFRAMEWORK_WORKSPACE=$S/$SW/work" AGENTFRAMEWORK_PY_RUN=1 \
        AGENTFRAMEWORK_R1_CONTRACT=1 AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$S/$SW/transcript.json" "AGENTFRAMEWORK_R1_TAG=R544-probe-smoke-on" \
        timeout 300 "$BIN" -q "$(cat "$S/task.txt")" --output-mode text --session-id "r544-smoke-on" \
        > "$S/$SW/reply.txt" 2> "$S/$SW/stderr.txt"
  else
    env -u AGENTFRAMEWORK_R1_ROLE_FILE -u AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK \
        "AGENTFRAMEWORK_WORKSPACE=$S/$SW/work" AGENTFRAMEWORK_PY_RUN=1 \
        AGENTFRAMEWORK_R1_CONTRACT=1 \
        "AGENTFRAMEWORK_R1_TRANSCRIPT=$S/$SW/transcript.json" "AGENTFRAMEWORK_R1_TAG=R544-probe-smoke-off" \
        timeout 300 "$BIN" -q "$(cat "$S/task.txt")" --output-mode text --session-id "r544-smoke-off" \
        > "$S/$SW/reply.txt" 2> "$S/$SW/stderr.txt"
  fi
  echo "$SW cli_rc=$?"
done

python3 - "$S" > "$S/verdict.txt" 2>&1 <<'PY'
import io, json, os, re, sys
S = sys.argv[1]
def load(sw):
    p = os.path.join(S, sw, "transcript.json")
    if not os.path.isfile(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
on, off = load("on"), load("off")
reply_on = io.open(os.path.join(S, "on", "reply.txt"), encoding="utf-8", errors="replace").read() \
    if os.path.isfile(os.path.join(S, "on", "reply.txt")) else ""
rows = [
 ("on_ran_is_1", on.get("public_probe_ran") == 1, str(on.get("public_probe_ran"))),
 ("on_total_ge_1", (on.get("public_probe_total") or 0) >= 1, str(on.get("public_probe_total"))),
 ("on_reply_marker", "R1_PUBLIC_PROBE" in reply_on, "marker=%s" % ("R1_PUBLIC_PROBE" in reply_on)),
 ("off_field_absent", ("public_probe_ran" not in off) or (off.get("public_probe_ran") is None),
  str(off.get("public_probe_ran"))),
 ("off_reply_no_marker", "R1_PUBLIC_PROBE" not in io.open(os.path.join(S, "off", "reply.txt"),
  encoding="utf-8", errors="replace").read() if os.path.isfile(os.path.join(S, "off", "reply.txt")) else True,
  "n/a"),
 ("on_rc_recorded", on.get("rc") is not None, "rc=%s stage=%s probe_failed=%s" % (
     on.get("rc"), on.get("stage"), on.get("public_probe_failed"))),
]
bad = 0
for name, ok, got in rows:
    if not ok:
        bad += 1
    print("  %-22s %-5s %s" % (name, "PASS" if ok else "FAIL", got))
print("PROBE_SMOKE_VERDICT=%s" % ("PASS" if bad == 0 else "FAIL(%d)" % bad))
sys.exit(0 if bad == 0 else 1)
PY
vrc=$?
cat "$S/verdict.txt"
echo "PROBE_SMOKE_RC=$vrc"
exit "$vrc"
