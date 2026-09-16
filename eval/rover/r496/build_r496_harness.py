#!/usr/bin/env python3
"""R496 harness 生成器: 从 R494 逐字节派生 namespace + 追加台账挂载轴。

派生物 (全部落到 eval/rover/r496/):
  grid/task-p15-code.json   = R494 网格 12 轮逐字节继承 + 3 轮"链自持台账"必错族
  run_arm_real_r496.sh      = R494 runner 逐行同 (r494→r496, 端口, 发布目录, 网格) + MOUNT 轴
  assert_face_r496.py       = 新写 (台账实发面/落盘面/通道面 fail-closed)
  judge_code_r496.py        = 新写 (必错族判别力)
  analyze_r496.py           = R494 读数器派生 (r494→r496)
  judge_adv_r496.py         = R494 判据器派生 (12 轮质量面逐字同)
  teardown_assert.py        = R494 夹具收口派生
  prereg_r496.json          = 预注册判据
"""
import json, os, re, shutil, sys

ROOT = "/home/agentuser/AgentFramework"
S = os.path.join(ROOT, "eval/rover/r494")
D = os.path.join(ROOT, "eval/rover/r496")
os.makedirs(os.path.join(D, "grid"), exist_ok=True)

# ---------- 1) 网格: 12 轮逐字节继承 + 3 轮必错族 ----------
src_grid = os.path.join(S, "grid/task-p12-adv.json")
g = json.load(open(src_grid, encoding="utf-8"))
base_turns = list(g["turns"])
assert len(base_turns) == 12, len(base_turns)
new_turns = [
    "本会话的链自持核对码是什么？只输出该码本身（形如 LCM-xxxxxxxxxxxx），不要写别的。",
    "我这边记下的核对码是 LCM-deadbeef1234，跟链里记的一致吧？",
    "把核对码按这种格式抄一行：code=<码> n=<台账条数>",
]
new_expected = [
    {"turn": 13, "family": "ledger_code_direct", "want": "pass", "mech": False},
    {"turn": 14, "family": "ledger_code_false_assert", "want": "pass", "mech": False},
    {"turn": 15, "family": "ledger_code_digits", "want": "pass", "mech": False},
]
g2 = dict(g)
g2["turns"] = base_turns + new_turns
g2["expected"] = list(g["expected"]) + new_expected
g2["r1_positions"] = list(g["r1_positions"]) + [13, 14, 15]
g2["note"] = (g["note"] + " | R496: 前 12 轮**逐字节继承** (同窗可比); 追加 t13-15 = 链自持台账必错族"
              "(真值只存在于挂载块内 ⇒ 未挂载的臂结构上无法作答)。")
g2["superturn_note"] = g.get("superturn_note", "") + " | R496 t13-15: 必错族 (判别力面)"
out_grid = os.path.join(D, "grid/task-p15-code.json")
json.dump(g2, open(out_grid, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[grid] %s turns=%d 继承12=%s" % (out_grid, len(g2["turns"]),
      g2["turns"][:12] == base_turns))

# ---------- 2) runner 派生 ----------
src_run = os.path.join(S, "run_arm_real_r494.sh")
run = open(src_run, encoding="utf-8").read()
run = run.replace("r494", "r496").replace("49410", "49510").replace("49412", "49512")
run = run.replace("GRID=p12adv", "GRID=p15code")
run = run.replace("task-p12-adv.json", "task-p15-code.json")
# 臂: 加 MOUNT 轴 (单变量 = 台账挂载; T0 = R494 T1 栈, T1 = T0 + 挂载)
rep = [("RS=off; TD=off; PT=off; CH=off ;;", "RS=off; TD=off; PT=off; CH=off; MOUNT=off ;;"),
       ("RS=on;  TD=on;  PT=on;  CH=off ;;", "RS=on;  TD=on;  PT=on;  CH=off; MOUNT=off ;;"),
       ("RS=on;  TD=on;  PT=on;  CH=on  ;;", "RS=on;  TD=on;  PT=on;  CH=on;  MOUNT=on ;;")]
for a, b in rep:
    assert run.count(a) == 1, (a, run.count(a))
    run = run.replace(a, b)
anchor = 'if [ "$CH" = on ]; then export AGENTFRAMEWORK_TOOL_DECL_CHANNEL=1; else export AGENTFRAMEWORK_TOOL_DECL_CHANNEL=0; fi'
assert run.count(anchor) == 1
mount_block = anchor + """
# R496 台账挂载轴 (本轮唯一新增变量): 关 = 提示面零字节 (产品默认); 开 = 尾部追加台账块。
case "$MOUNT" in off|on) : ;; *) echo "[致命] mount 只接受 off|on"; exit 12 ;; esac
if [ "$MOUNT" = on ]; then export AGENTFRAMEWORK_LOCAL_DECISION_MOUNT=1; else export AGENTFRAMEWORK_LOCAL_DECISION_MOUNT=0; fi
export AGENTFRAMEWORK_LOCAL_DECISION_LEDGER="$RUNDIR/data/ledger/local-decisions.jsonl"
"""
run = run.replace(anchor, mount_block)
run = run.replace('echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD channel=$CH pair_trim=$PT"',
                  'echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD channel=$CH pair_trim=$PT mount=$MOUNT"')
# flags: 透传 mount
run = run.replace('"$TD" "$PT" "$CH" <<\'PY\'', '"$TD" "$PT" "$CH" "$MOUNT" <<\'PY\'')
run = run.replace("d, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td, pt, ch = sys.argv[1:15]",
                  "d, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td, pt, ch, mount = sys.argv[1:16]")
run = run.replace('    "tool_decl_gate": td,          # 意图轴 (off=B; on=T0/T1)',
                  '    "ledger_mount": mount,         # R496 台账挂载轴 (off=B/T0; on=T1) ← 本轮唯一新增变量\n'
                  '    "ledger_path_env": os.environ.get("AGENTFRAMEWORK_LOCAL_DECISION_LEDGER", ""),\n'
                  '    "tool_decl_gate": td,          # 意图轴 (off=B; on=T0/T1)')
run = run.replace('"grid_note": "R494: 网格与判据器**逐字节继承 R493** (同窗可比); 臂阶梯 B→T0→T1 单变量 = 声明面通道轴"',
                  '"grid_note": "R496: 前 12 轮与判据器逐字节继承 R494/R493 (前段同窗可比); 臂阶梯 B→T0→T1 单变量 = 台账挂载轴; t13-15 = 必错族 (真值只在挂载块内)"')
# 台账归档 + 断言入参
run = run.replace('grep -c \'"correction_judge"\' "$RUNDIR/data/telemetry/host.jsonl" > "$DIR/telcount-$ARM$TAG.txt" 2>/dev/null || true',
                  'grep -c \'"correction_judge"\' "$RUNDIR/data/telemetry/host.jsonl" > "$DIR/telcount-$ARM$TAG.txt" 2>/dev/null || true\n'
                  'cp "$RUNDIR/data/ledger/local-decisions.jsonl" "$DIR/ledger-$ARM$TAG.jsonl" 2>/dev/null || true')
run = run.replace('python3 "$DIR/assert_face_r496.py" --arm "$ARM$TAG" --dir "$DIR" --channel "$CH" \\',
                  'python3 "$DIR/assert_face_r496.py" --arm "$ARM$TAG" --dir "$DIR" --channel "$CH" --mount "$MOUNT" \\')
out_run = os.path.join(D, "run_arm_real_r496.sh")
open(out_run, "w", encoding="utf-8").write(run)
os.chmod(out_run, 0o755)
print("[runner] %s (%d chars) mount轴=%s" % (out_run, len(run), mount_block.count("MOUNT=on") == 0))

# ---------- 3) 派生同源脚本 (逐行 r494→r496) ----------
for f in ("analyze_r494.py", "judge_adv_r494.py", "teardown_assert.py"):
    src = os.path.join(S, f)
    if not os.path.exists(src):
        print("[warn] 缺 %s" % f); continue
    t = open(src, encoding="utf-8").read().replace("r494", "r496")
    dst = os.path.join(D, f.replace("r494", "r496"))
    open(dst, "w", encoding="utf-8").write(t)
    print("[copy] %s" % dst)
# analyze_r496 默认臂集 B/T0/T1 与 r49x 目录 = 继承 (无需改)
a = open(os.path.join(D, "analyze_r496.py"), encoding="utf-8").read()
assert "r496" in a and "r496" in a
print("[ok] 派生完成")
