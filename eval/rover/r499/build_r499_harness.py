#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R499 臂执行器/aux 机派生器 (通用代码逻辑, 语言无关)。

从 eval/rover/r497 派生到 eval/rover/r499 (唯一改动入口; 逐条替换带计数断言, 失败即不写盘)。

R499 相对 R497 的差异 (逐条):
  N1  命名空间: r497→r499 (DIR / 端口 49910,49912 / canary 路径与 token / --round R499 / 日志前缀)
  N2  被测二进制: /tmp/pub_r499/agenthost (本轮重发布; sha 记入 flags-*.json)
  N3  **唯一新变量** = 本地改写通道闸 `AGENTFRAMEWORK_LOCAL_PARAPHRASE` (产品只认字面 "1")
      ⇒ 人面 on|off 必须显式映射成 1/0 (直传 "on" 会被静默当关) + flags 记 `local_paraphrase`
  N4  臂矩阵: 6 臂 → 2 形状 (C = 基线全开 P 关; P = 同基线 + 改写通道开), 用 tag 区分重复跑:
        C(1 跑) / P1,P2,P3 (n=3) ⇒ 同窗单变量 + 质量面 n≥3
  N5  aux 同批携带 (teardown_assert / assert_face / face_ext) 且逐字节断言 + runner 起手 fail-closed
  N6  网格逐字节继承 (p17code; t8 = 改写触发轮) — 两臂同网格, 记 sha
"""
import io, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, "eval/rover/r497")
DST = HERE

errs = []


def rep(s, old, new, name, expect=None):
    n = s.count(old)
    if expect is not None and n != expect:
        errs.append("%s: 期望 %d 处, 实得 %d (%r)" % (name, expect, n, old[:40]))
    if n == 0:
        errs.append("%s: 锚点缺失 (%r)" % (name, old[:40]))
    return s.replace(old, new)


# ── N1/N2/N3/N4: runner ────────────────────────────────────────────────────
src = io.open(os.path.join(SRC, "run_arm_real_r497.sh"), encoding="utf-8").read()
out = src
out = rep(out, "r497", "r499", "N1 小写命名空间")
out = rep(out, "R497", "R499", "N1 大写命名空间")
out = rep(out, "49710", "49910", "N1 中继端口", expect=1)
out = rep(out, "49712", "49912", "N1 API 端口", expect=1)
# 说明段 (相对 R499 的差异): 用本轮真实的差异表替换继承来的说明
old_hdr_start = out.index("# 相对 R496 的差异:")
old_hdr_end = out.index("# 用法: bash run_arm_real_r499.sh")
new_hdr = """# 相对 R497 的差异 (R499):
#   1) 命名空间 r497 → r499 (DIR / 端口 49910,49912 / canary / 轮号)
#   2) 被测二进制 = **R499 重新 AOT 发布产物** (/tmp/pub_r499/agenthost): R498 改了链代码
#      (③ 内容承载的本地改写通道 / ② 遥测环 / ④ 文件面越界闸) ⇒ 必须重发布
#   3) **唯一新变量** = 本地改写通道闸 AGENTFRAMEWORK_LOCAL_PARAPHRASE (产品只认字面 "1")
#      ⇒ 人面 on|off 显式映射 1/0; 直传 "on" 会被静默当关 (臂自称开、产品实则关) ⇒ flags 记 local_paraphrase
#   4) 臂矩阵 2 形状 + tag: C(1 跑, 改写关 = 同窗对照) / P1,P2,P3(n=3, 改写开)
#      基线 = R497 T1 形状 (gate/skip/声明门/pair_trim/通道/挂载/boundary 全开)
#   5) aux 同批携带 + 起手 fail-closed; 网格 p17code 逐字节继承 (t8 = 改写触发轮)
#
"""
out = out[:old_hdr_start] + new_hdr + out[old_hdr_end:]
# 臂矩阵: 6 → 2
old_case = """case "$ARM" in
  B|T0|T2|T1|T1n|O1) CWD_NAME=run-$ARM$TAG ;;
  *) echo "[致命] 未知臂: $ARM"; exit 2 ;;
esac"""
new_case = """case "$ARM" in
  C|P) CWD_NAME=run-$ARM$TAG ;;
  *) echo "[致命] 未知臂: $ARM (仅 C|P)"; exit 2 ;;
esac"""
out = rep(out, old_case, new_case, "N4 臂名白名单", expect=1)
old_matrix = """case "$ARM" in
  B)   MP=$M3B; GATE=false; RJ=true; ROLE="$ROLE_GROWTH"; RS=off; TD=off; PT=off; CH=off; MOUNT=off; AB=on ;;
  T0)  MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=off; MOUNT=off; AB=on ;;
  T2)  MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=on;  MOUNT=off; AB=on ;;
  T1)  MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=on;  MOUNT=on;  AB=on ;;
  T1n) MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=off; TD=on;  PT=on;  CH=on;  MOUNT=on;  AB=on ;;
  O1)  MP=$M3B; GATE=true;  RJ=true; ROLE="$ROLE_GROWTH"; RS=on;  TD=on;  PT=on;  CH=off; MOUNT=off; AB=off ;;
esac"""
new_matrix = """case "$ARM" in
  C) MP=$M3B; GATE=true; RJ=true; ROLE="$ROLE_GROWTH"; RS=on; TD=on; PT=on; CH=on; MOUNT=on; AB=on; PP=off ;;
  P) MP=$M3B; GATE=true; RJ=true; ROLE="$ROLE_GROWTH"; RS=on; TD=on; PT=on; CH=on; MOUNT=on; AB=on; PP=on  ;;
esac"""
out = rep(out, old_matrix, new_matrix, "N4 臂矩阵", expect=1)
# N3: 改写闸显式映射 (插在 boundary 块之后)
anchor = 'if [ "$AB" = on ]; then export AGENTFRAMEWORK_ACTION_BOUNDARY=1; else export AGENTFRAMEWORK_ACTION_BOUNDARY=0; fi\n'
pp_block = anchor + """# R499 **唯一新变量**: 本地改写通道 (内容承载的本地生成; 产品只认字面 "1")
case "$PP" in off|on) : ;; *) echo "[致命] paraphrase 只接受 off|on (got=$PP)"; exit 12 ;; esac
if [ "$PP" = on ]; then export AGENTFRAMEWORK_LOCAL_PARAPHRASE=1; else export AGENTFRAMEWORK_LOCAL_PARAPHRASE=0; fi
"""
out = rep(out, anchor, pp_block, "N3 改写闸映射", expect=1)
out = rep(out, 'echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD channel=$CH pair_trim=$PT mount=$MOUNT boundary=$AB"',
          'echo "[arm] $ARM model_path=$MP gate=$GATE rj=$RJ repeat_skip=$RS tool_decl_gate=$TD channel=$CH pair_trim=$PT mount=$MOUNT boundary=$AB paraphrase=$PP"',
          "N3 回显", expect=1)
# flags: argv 追加 PP, 字段与回显
out = rep(out, '"$TAG" "$TD" "$PT" "$CH" "$MOUNT" "$AB" <<\'PY\'',
          '"$TAG" "$TD" "$PT" "$CH" "$MOUNT" "$AB" "$PP" <<\'PY\'', "N3 argv", expect=1)
out = rep(out, "tag, td, pt, ch, mount, ab = sys.argv[1:17]",
          "tag, td, pt, ch, mount, ab, pp = sys.argv[1:18]", "N3 解包", expect=1)
out = rep(out, '    "replay_pair_trim": pt,        # off=B; on=T0/T1\n',
          '    "replay_pair_trim": pt,        # off=B; on=T0/T1\n'
          '    "local_paraphrase": pp,        # R499 **唯一新变量**: 内容承载的本地改写通道 (本地生成, 不付费)\n',
          "N3 flags 字段", expect=1)
out = rep(out, '"tool_decl_channel", "replay_pair_trim", "rundir_cwd")',
          '"tool_decl_channel", "replay_pair_trim", "local_paraphrase", "rundir_cwd")', "N3 flags 回显", expect=1)
# 网格: p17code 逐字节继承
out = rep(out, "TASK=$DIR/grid/task-p17-code.json", "TASK=$DIR/grid/task-p17-code.json", "N6 网格路径", expect=1)

# ── N5: aux 同批携带 ───────────────────────────────────────────────────────
AUX = ["teardown_assert.py", "assert_face_r497.py", "face_ext_r497.py", "judge_adv_r497.py"]
for a in AUX:
    s = io.open(os.path.join(SRC, a), encoding="utf-8").read()
    s2 = s.replace("r497", "r499").replace("R497", "R499")
    dst = os.path.join(DST, a.replace("r497", "r499"))
    io.open(dst, "w", encoding="utf-8").write(s2)
    if "r497" in s2 or "R497" in s2:
        errs.append("N5 aux 残留旧命名空间: " + a)
    if not os.path.exists(dst):
        errs.append("N5 aux 未落盘: " + dst)
# 网格逐字节
os.makedirs(os.path.join(DST, "grid"), exist_ok=True)
gsrc = os.path.join(SRC, "grid/task-p17-code.json")
gdst = os.path.join(DST, "grid/task-p17-code.json")
shutil.copyfile(gsrc, gdst)
if io.open(gsrc, "rb").read() != io.open(gdst, "rb").read():
    errs.append("N6 网格复制不一致")

if errs:
    print("[致命] 派生断言未过 ⇒ 不写盘:")
    for e in errs:
        print("   -", e)
    sys.exit(2)

rp = os.path.join(DST, "run_arm_real_r499.sh")
io.open(rp, "w", encoding="utf-8").write(out)
diff = os.popen("diff -u %s %s" % (os.path.join(SRC, "run_arm_real_r497.sh"), rp)).read()
io.open(os.path.join(DST, "run_arm_real_r499.diff"), "w", encoding="utf-8").write(diff)
print("[ok] 派生 %s (%d 字节); 差异 %d 行" % (rp, len(out), diff.count("\n")))
