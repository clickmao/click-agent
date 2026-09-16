#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R492 臂执行器机派生器 (通用代码逻辑, 语言无关)

从 eval/rover/r491/run_arm_real_r491.sh 派生 eval/rover/r492/run_arm_real_r492.sh。
本文件是**唯一**改动入口: 所有差异在此显式声明, 派生后立即做 fail-closed 断言 (断言不过 ⇒ 不写盘)。

本轮新增 (相对 R491):
  N1 命名空间 491 → 492 (目录/键名/默认端口/轮号/默认二进制)
  N2 **显式**回放配对剪裁开关: 第 5 位置参数 PAIR_TRIM (off|on)
     ⇒ export AGENTFRAMEWORK_REPLAY_PAIR_TRIM="$PAIR_TRIM" 并写入 flags-*.json ("replay_pair_trim")
     (R491 铁律: 开关不得"未设=默认"含糊; 未跑臂禁豁免)
  N3 flags 写入器多收一个入参 (pt), 并回显 replay_pair_trim
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "eval", "rover", "r491", "run_arm_real_r491.sh")
DST = os.path.join(HERE, "run_arm_real_r492.sh")
DIFF = os.path.join(HERE, "run_arm_real_r492.diff")

src = io.open(SRC, encoding="utf-8").read()
out = src

# ── N1 命名空间 ──────────────────────────────────────────────────────────
out = out.replace("r491", "r492").replace("R491", "R492")
out = out.replace("R489 版机派生", "R491 版机派生")   # 派生面向上一轮, 保持史实
# ── N5 aux 同批携带 (R491 器具修缮#1: 派生器必带 aux, 缺失即拒跑) ♻ 本轮自伤修正 ──
import shutil
_aux = [("eval/rover/r491/teardown_assert.py", "eval/rover/r492/teardown_assert.py")]
for _s, _d in _aux:
    shutil.copyfile(_s, _d)                       # 该器具无轮号字面量 ⇒ 逐字节同源
    assert open(_d, "rb").read() == open(_s, "rb").read(), "aux 复制不一致: " + _d
_aux_guard = ('for f in teardown_assert.py; do [ -f "$DIR/$f" ] || '
              '{ echo "[致命] aux 缺失: $f ⇒ 拒跑 (防 teardown 空跑泄漏)"; exit 12; }; done\n')
assert 'DIR=$ROOT/eval/rover/r492\n' in out, "aux 注入锚点缺失"
out = out.replace('DIR=$ROOT/eval/rover/r492\n', 'DIR=$ROOT/eval/rover/r492\n' + _aux_guard)
out = out.replace("相对 R489 的差异逐条", "相对 R491 的差异逐条 (R491 自身差异见其 diff)")
out = out.replace(
    "#      (声明面按需 ToolDeclGate + 回放剪裁 ReplayTrimmedLocalTemplates), 四臂**同一产物**\n",
    "#      (声明面按需 ToolDeclGate + 回放剪裁 ReplayTrimmedLocalTemplates), 四臂**同一产物**\n"
    "#   4b) R492 新增: 第 5 位置参数 pair_trim (off|on) ⇒ **显式**导出\n"
    "#      AGENTFRAMEWORK_REPLAY_PAIR_TRIM 并写入 flags-*.json; 同一二进制内两态可比\n"
    "#      (闸关 = 对照臂 TC; 闸开 = TP1..TP3), 差异只在开关 ⇒ 单变量\n")
# 裸端口/轮号字面量 (无 r/R 前缀, 上面的替换不覆盖)
out = out.replace("49110", "49210").replace("49112", "49212").replace("49114", "49214")
out = out.replace("49116", "49216").replace("49118", "49218").replace("49120", "49220")
out = out.replace("49122", "49222").replace("49124", "49224")
# ── N2 显式剪裁开关 ──────────────────────────────────────────────────────
out = out.replace(
    '用法: run_arm_real_r492.sh <Arole|R|T> [tag] [relay_port] [api_port]',
    '用法: run_arm_real_r492.sh <Arole|R|T> [tag] [relay_port] [api_port] [pair_trim:off|on]')
out = out.replace(
    'API_PORT=${4:-49212}',
    'API_PORT=${4:-49212}\nPAIR_TRIM=${5:-off}')
out = out.replace(
    'export AGENTFRAMEWORK_TOOL_DECL_GATE=$TD\n',
    'export AGENTFRAMEWORK_TOOL_DECL_GATE=$TD\n'
    '# R492 回放配对剪裁: **显式**导出 (默认关 ⇒ 与 R491 逐字节同行为; on = 剔除零远端调用轮的 user 侧回放)\n'
    'case "$PAIR_TRIM" in off|on) : ;; *) echo "[致命] pair_trim 只接受 off|on (got=$PAIR_TRIM)"; exit 12 ;; esac\n'
    '# 产品取值只认 1/true (ReplayPairTrim.Decide) ⇒ 人面 on|off 必须**显式映射**,\n'
    '# 否则 "on" 会被静默当关 (假阴性: 臂自称门开、产品实则门关)。\n'
    'if [ "$PAIR_TRIM" = on ]; then export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=1; else export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=0; fi\n')
out = out.replace(
    'echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD"',
    'echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD pair_trim=$PAIR_TRIM"')
out = out.replace(
    'CWD_NAME=run-$ARM$TAG',
    'CWD_NAME=run-$ARM$TAG$([ "$PAIR_TRIM" = on ] && echo -pt)')
# ── N3 flags 写入器 ─────────────────────────────────────────────────────
out = out.replace(
    '"$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" "$TAG" "$TD" <<\'PY\'',
    '"$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" "$TAG" "$TD" "$PAIR_TRIM" <<\'PY\'')
out = out.replace(
    'd, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td = sys.argv[1:13]',
    'd, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag, td, pt = sys.argv[1:14]')
out = out.replace(
    '    "tool_decl_gate": td,   # R492: 声明面按需开关 (off=门关 ⇒ 与 R456..R489 逐字节同; on=按意图丢声明)',
    '    "tool_decl_gate": td,   # R492: 声明面按需开关 (off=门关 ⇒ 与 R456..R489 逐字节同; on=按意图丢声明)\n'
    '    "replay_pair_trim": pt,  # R492: 回放配对剪裁开关 (off=与 R491 同; on=剔除零远端调用轮的 user 侧)')
out = out.replace(
    '("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "tool_decl_gate", "rundir_cwd")',
    '("arm_class_note", "turn_gate", "relation_judge", "repeat_skip", "tool_decl_gate",\n                            "replay_pair_trim", "rundir_cwd")')

# ── fail-closed 断言 (不过 ⇒ 不写盘) ────────────────────────────────────
asserts = [
    ("N1 目录", "eval/rover/r492" in out and "eval/rover/r491" not in out),
    ("N1 键名", "R492_UPSTREAM_KEY" in out and "R491_UPSTREAM_KEY" not in out),
    ("N1 轮号", "--round R492" in out),
    ("N1 端口", "49210" in out and "49110" not in out),
    ("N2 入参", "PAIR_TRIM=${5:-off}" in out),
    ("N2 导出", 'export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=1' in out and 'export AGENTFRAMEWORK_REPLAY_PAIR_TRIM=0' in out),
    ("N2 人面→产品映射", 'AGENTFRAMEWORK_REPLAY_PAIR_TRIM=$PAIR_TRIM' not in out),
    ("N5 aux 携带+起手预检", 'aux 缺失: $f' in out and os.path.exists("eval/rover/r492/teardown_assert.py")),
    ("N2 取值校验", 'case "$PAIR_TRIM" in off|on)' in out),
    ("N3 入参", "sys.argv[1:14]" in out),
    ("N3 字段", '"replay_pair_trim": pt' in out),
    ("N3 回显", '"replay_pair_trim", "rundir_cwd")' in out),
    ("史实", "R491 版机派生" in out),
    ("夹具/网格未动", 'GRID=p12' in out and '/r438/grid/task-$GRID.json' in out),
]
bad = [n for n, ok in asserts if not ok]
if bad:
    print("[致命] 派生断言未过: %s ⇒ 不写盘" % ", ".join(bad))
    sys.exit(2)
io.open(DST, "w", encoding="utf-8").write(out)
os.chmod(DST, 0o755)
os.system("diff -u %s %s > %s" % (SRC, DST, DIFF))
print("[ok] 派生 %s (%d 字节); 差异 %d 行 → %s" % (DST, len(out.encode()), sum(1 for _ in io.open(DIFF, encoding="utf-8")), DIFF))
