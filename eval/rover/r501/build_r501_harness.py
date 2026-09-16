#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R501 臂执行器/aux 机派生器 (通用代码逻辑, 语言无关)。

从 eval/rover/r499 派生到 eval/rover/r501 (唯一改动入口; 逐条替换 + **残留零断言**, 失败即不写盘)。

R501 相对 R499 的差异 (逐条):
  N1  命名空间: r499→r501 (DIR / 端口 50110,50112 / canary / --round R501 / 日志前缀 / 上游 key 变量名)
  N2  被测二进制: /tmp/pub_r501/agenthost (**本轮唯一 src 改动** = IndustrialAgentV2.cs 改写族豁免后重发布)
  N3  臂矩阵形状**不变** (= R499: C 改写关 / P 改写开) ⇒ 唯一变量只有二进制 ⇒ 跨轮同形可比
  N4  aux 同批携带 (含改名) 且**引用一致性机检**: runner 里出现的每个 aux 文件名必须在 DST 存在
  N5  网格逐字节继承 (p17code; t8 = 改写触发轮)
  N6  判据器**逐字节继承 r499 名** (跨轮同仪器; 判据器改版禁跨轮相减)
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, "eval/rover/r499")
DST = HERE
errs = []


def rep(s, old, new, name, expect=None):
    n = s.count(old)
    if expect is not None and n != expect:
        errs.append("%s: 期望 %d 处, 实得 %d (%r)" % (name, expect, n, old[:40]))
    if n == 0:
        errs.append("%s: 锚点缺失 (%r)" % (name, old[:40]))
    return s.replace(old, new)


src = io.open(os.path.join(SRC, "run_arm_real_r499.sh"), encoding="utf-8").read()
out = src
out = rep(out, "r499", "r501", "N1 小写命名空间")
out = rep(out, "R499", "R501", "N1 大写命名空间")
out = rep(out, "49910", "50110", "N1 中继端口", expect=1)
out = rep(out, "49912", "50112", "N1 API 端口", expect=1)
# 说明段: 换成 R501 的真实差异表
hs = out.index("# 相对 R499 的差异 (R499):") if "# 相对 R499 的差异 (R499):" in out else out.index("# 相对 R497 的差异 (R501):")
he = out.index("# 用法: bash run_arm_real_r501.sh")
new_hdr = """# 相对 R499 的差异 (R501):
#   1) 命名空间 r499 → r501 (DIR / 端口 50110,50112 / canary / 轮号 / 上游 key 变量名)
#   2) 被测二进制 = **R501 重新 AOT 发布产物** (/tmp/pub_r501/agenthost): 本轮改了链代码
#      (IndustrialAgentV2.cs 改写族豁免 —— R500 实证的吸收后被 R444 后置否决吞掉) ⇒ 必须重发布
#   3) 臂矩阵形状与 R499 **完全相同** (C 改写关 / P 改写开) ⇒ 唯一变量只有二进制字节
#      ⇒ C 臂同时充作「闸关时逐位不变」的跨版本对照
#   4) aux 同批携带 + **引用一致性机检** + 起手 fail-closed
#
"""
out = out[:hs] + new_hdr + out[he:]
# 残留零断言 (fail-closed): 旧命名空间/旧端口不得留在**可执行行**里 (注释是散文, 不计)
for ln in out.split("\n"):
    if ln.lstrip().startswith("#"):
        continue
    for bad in ["r499", "R499", "49910", "49912"]:
        if bad in ln:
            errs.append("N1 可执行行残留旧命名空间/端口 (%s): %s" % (bad, ln.strip()[:90]))
# 网格
out = rep(out, "TASK=$DIR/grid/task-p17-code.json", "TASK=$DIR/grid/task-p17-code.json", "N5 网格路径", expect=1)

# ── N4: aux 同批携带 (含改名) ──────────────────────────────────────────────
AUX = ["teardown_assert.py", "assert_face_r499.py", "face_ext_r499.py", "judge_adv_r499.py"]
written = []
for a in AUX:
    s = io.open(os.path.join(SRC, a), encoding="utf-8").read()
    s2 = s.replace("r499", "r501").replace("R499", "R501")
    d = os.path.join(DST, a.replace("r499", "r501"))
    io.open(d, "w", encoding="utf-8", newline="\n").write(s2)
    written.append(os.path.basename(d))
    if "r499" in s2 or "R499" in s2:
        errs.append("N4 aux 残留旧命名空间: " + a)
# 引用一致性: **本派生器落盘的** aux 必须逐个被 runner 引用到 (R499 教训: 改名不同步 ⇒ N5 断言失败)
for base in written:
    if base not in out:
        errs.append("N4 aux 已落盘但 runner 未引用: " + base)
ext = set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*\.py)", out)) - set(written)
print("[aux]", ",".join(written), "| 外部引用(不计)", ",".join(sorted(ext)))

# 网格逐字节
os.makedirs(os.path.join(DST, "grid"), exist_ok=True)
gsrc = os.path.join(SRC, "grid/task-p17-code.json")
gdst = os.path.join(DST, "grid/task-p17-code.json")
io.open(gdst, "wb").write(io.open(gsrc, "rb").read())
if io.open(gsrc, "rb").read() != io.open(gdst, "rb").read():
    errs.append("N5 网格复制不一致")

if errs:
    print("[致命] 派生断言未过 ⇒ 不写盘:")
    for e in errs:
        print("   -", e)
    sys.exit(2)

rp = os.path.join(DST, "run_arm_real_r501.sh")
io.open(rp, "w", encoding="utf-8", newline="\n").write(out)
diff = os.popen("diff -u %s %s" % (os.path.join(SRC, "run_arm_real_r499.sh"), rp)).read()
io.open(os.path.join(DST, "run_arm_real_r501.diff"), "w", encoding="utf-8", newline="\n").write(diff)
print("[ok] 派生 %s (%d 字节); 差异 %d 行; 网格逐字节同" % (rp, len(out), diff.count("\n")))
