#!/usr/bin/env python3
"""R488: 由 R487 臂执行器**机派生** R488 臂执行器与 both 驱动器 (禁手抄 + 禁改历史证据)。

语言无关: 纯文本派生 + 逐条计数断言, 不依赖被派生脚本的语言特性。
派生规则 (每条断言出现次数, 少/多一处即 rc=2 fail-closed, 不写盘):
  1) 命名空间: r487 → r488 (DIR / both 脚本路径 / key 变量名 / round 参数 / 日志前缀)
  2) 候选① 臂矩阵: 2x2 析因 (B=门关+rs关 / G=门开+rs关 / S=门关+rs开 / R=门开+rs开),
     同一二进制 (只翻开关) ⇒ 隔离 turn_gate 与 repeat_skip 的单独效应
  3) 候选④ 真值列命名空间: relay 传 TAG (原传 $ARM ⇒ Arole485/R485 的真值列落共用名 usage-Arole.jsonl,
     臂自身 usage-<ARM><TAG>.jsonl 恒 0 字节, 已在 R487 记为器具缺陷) + tel-/telcount- 一并并入 TAG
  4) both 驱动器: 四臂顺序执行 (B → G → S → R), 起手闸前置 fail-closed (单一源器具, 本脚本零阈值字面量)
历史证据不动: R487/R482/R477 器具与其读数字节不改 (只读)。
三态: rc=0 派生完成并写盘 / rc=2 断言失败 (fail-closed) / rc=3 缺输入。
"""
import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC_ARM = ROOT / "eval" / "rover" / "r487" / "run_arm_real_r487.sh"
SRC_BOTH = ROOT / "eval" / "rover" / "r487" / "run_both_r487.sh"
OUTD = ROOT / "eval" / "rover" / "r488"

# ---- 替换表: (旧, 新, 期望次数) ---- 顺序敏感: 先改名, 再改块 ----
ARM_RULES = [
    # 0) 头注释: 差异说明整块改写
    ("# R487 臂执行器 —— 由 R482 版**机派生** (eval/rover/r487/derive_r487.py: 替换表逐条计数断言, 差异见 derive_r487.diff)。",
     "# R488 臂执行器 —— 由 R487 版**机派生** (eval/rover/r488/derive_r488.py: 替换表逐条计数断言, 差异见 derive_r488.diff)。",
     1),
    ("#   相对 R482 的差异逐条:\n"
     "#   1) DIR r482 → r487 (读数命名空间隔离)\n"
     "#   2) 默认二进制 → /tmp/pub_r485/agenthost (含 R485 微问询预发送闸)\n"
     "#   3) 新增 TAG 维度 ⇒ arm_key = ARM+TAG (A0 / Arole485 / R485 三臂读数互不覆盖; TAG 空时与 R482 形态逐字同)\n"
     "#   4) 候选⑦: 删除脚本内手抄的起手闸常数 ⇒ 改调单一源 eval/rover/r483/preflight_gate.py (本文件零阈值字面量)\n"
     "#   5) A0 臂 = 与 Arole 同臂参 (门关 + rj 开 + repeat_skip off), 只换二进制 ⇒ 隔离微闸单独效应",
     "#   相对 R487 的差异逐条:\n"
     "#   1) 命名空间 r487 → r488 (DIR / round / key 变量名)\n"
     "#   2) 候选①: 臂矩阵改 **2x2 析因** (B=Arole / G / S / R) —— 同二进制只翻开关, 隔离 turn_gate 与 repeat_skip\n"
     "#   3) 候选④: TAG 并入 relay 命名 (原传 $ARM ⇒ Arole485/R485 真值列落共用名, 臂自身 usage-<ARM><TAG> 恒 0 字节) + tel-/telcount- 一并并入 TAG\n"
     "#   4) 二进制**不动** (/tmp/pub_r485/agenthost): 换二进制就无法与 R487 Arole485 基线比",
     1),
    ("#   A0    = 门关 + rj 开 + repeat_skip off + pub_r479v2 二进制 ← 生产等价分母锚\n"
     "#   Arole = 门关 + relation_judge=on  + pub_r485 二进制      ← 同二进制门关 (隔离微闸)\n"
     "#   R     = 门开 + rj=on + repeat_skip=on + pub_r485 二进制 ← 主判据面 (r1 在管道内)",
     "#   Arole = 门关 + rj=on + repeat_skip off (B 基线)  ← 同刻分母\n"
     "#   G     = 门开 + rj=on + repeat_skip off          ← turn_gate 单独效应\n"
     "#   S     = 门关 + rj=on + repeat_skip on           ← repeat_skip 单独效应\n"
     "#   R     = 门开 + rj=on + repeat_skip on           ← 生产形态 (r1 在管道内)",
     1),
    ("# 用法: bash run_arm_real_r487.sh <A0|Arole|R> [tag] [relay_port] [api_port]",
     "# 用法: bash run_arm_real_r488.sh <Arole|G|S|R> [tag] [relay_port] [api_port]",
     1),
    ("ARM=${1:?用法: run_arm_real_r487.sh <A0|Arole|R> [tag] [relay_port] [api_port]}",
     "ARM=${1:?用法: run_arm_real_r488.sh <Arole|G|S|R> [tag] [relay_port] [api_port]}",
     1),
    # 1) 命名空间
    ("DIR=$ROOT/eval/rover/r487", "DIR=$ROOT/eval/rover/r488", 1),
    ("R487_UPSTREAM_KEY", "R488_UPSTREAM_KEY", 3),
    ("--round R487", "--round R488", 1),
    # 2) 臂矩阵
    ("  A0|Arole) CWD_NAME=run-$ARM$TAG ;;\n  R)        CWD_NAME=run-$ARM$TAG ;;",
     "  Arole|G|S|R) CWD_NAME=run-$ARM$TAG ;;",
     1),
    ("  A0|Arole) MP=$M3B; GATE=false; RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=off ;;\n"
     "  R)     MP=$M3B; GATE=true;  RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=on  ;;",
     "  Arole) MP=$M3B; GATE=false; RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=off ;;\n"
     "  G)     MP=$M3B; GATE=true;  RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=off ;;\n"
     "  S)     MP=$M3B; GATE=false; RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=on  ;;\n"
     "  R)     MP=$M3B; GATE=true;  RJ=true;  ROLE=\"$ROLE_GROWTH\"; RS=on  ;;",
     1),
    # 3) 候选④: 真值列命名空间
    ("40 0.15 \"$DIR\" \"$ARM\" > \"$RELAYLOG\"", "40 0.15 \"$DIR\" \"$ARM$TAG\" > \"$RELAYLOG\"", 1),
    ("mkdir -p \"$DIR/tel-$ARM\"", "mkdir -p \"$DIR/tel-$ARM$TAG\"", 1),
    ("cp \"$RUNDIR/data/telemetry/host.jsonl\" \"$DIR/tel-$ARM/host.jsonl\"",
     "cp \"$RUNDIR/data/telemetry/host.jsonl\" \"$DIR/tel-$ARM$TAG/host.jsonl\"", 1),
    ("> \"$DIR/telcount-$ARM.txt\"", "> \"$DIR/telcount-$ARM$TAG.txt\"", 1),
    # 4) 陈旧自称标签 (只改自称, 不动历史引用句)
    ("# R487 候选⑦: 起手闸/沉降**单一源**", "# R488 候选⑦: 起手闸/沉降**单一源**", 1),
    ("# R487 臂 (端点 = 本地中继 v2 → 真供应商", "# R488 臂 (端点 = 本地中继 v2 → 真供应商", 1),
]

BOTH_RULES = [
    ("# R487 三臂顺序执行 (A0 → Arole485 → R485); key 只从 .env.local 取一次, 不回显。机派生自 run_both_r477.sh。",
     "# R488 四臂析因顺序执行 (B=Arole488b → G488g → S488s → R488r); key 只从 .env.local 取一次, 不回显。\n"
     "#   机派生自 eval/rover/r488/derive_r488.py (替换表逐条计数断言)。",
     1),
    ("# R487 候选⑦: 起手闸前置 (fail-closed; 单一源器具, 本脚本不自带 mem 判定)。",
     "# R488 候选⑦: 起手闸前置 (fail-closed; 单一源器具 eval/rover/r483/preflight_gate.py, 本脚本零 mem 阈值字面量)。",
     1),
    ("R487_UPSTREAM_KEY", "R488_UPSTREAM_KEY", 3),
    ("[both-r487]", "[both-r488]", 10),
    ("--round R487", "--round R488", 1),
    ("eval/rover/r487/preflight-both.json", "eval/rover/r488/preflight-both.json", 1),
    # 四臂块 (先改名后改块; 块内已是 [both-r488])
    ("AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r479v2/agenthost bash eval/rover/r487/run_arm_real_r487.sh A0 \"\" 48710 48712 || { echo \"[both-r488] A0 失败 rc=$?\"; exit 1; }\n"
     "echo \"[both-r488] A0 ok $(date +%H:%M:%S)\"\n"
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh Arole 485 48714 48713 || { echo \"[both-r488] Arole485 失败 rc=$?\"; exit 2; }\n"
     "echo \"[both-r488] Arole485 ok $(date +%H:%M:%S)\"\n"
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh R 485 48716 48715 || { echo \"[both-r488] R485 失败 rc=$?\"; exit 3; }\n"
     "echo \"[both-r488] R ok $(date +%H:%M:%S)\"",
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r488/run_arm_real_r488.sh Arole b 48810 48812 || { echo \"[both-r488] B 失败 rc=$?\"; exit 1; }\n"
     "echo \"[both-r488] B ok $(date +%H:%M:%S)\"\n"
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r488/run_arm_real_r488.sh G g 48814 48816 || { echo \"[both-r488] G 失败 rc=$?\"; exit 2; }\n"
     "echo \"[both-r488] G ok $(date +%H:%M:%S)\"\n"
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r488/run_arm_real_r488.sh S s 48818 48820 || { echo \"[both-r488] S 失败 rc=$?\"; exit 3; }\n"
     "echo \"[both-r488] S ok $(date +%H:%M:%S)\"\n"
     "AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r488/run_arm_real_r488.sh R r 48822 48824 || { echo \"[both-r488] R 失败 rc=$?\"; exit 4; }\n"
     "echo \"[both-r488] R ok $(date +%H:%M:%S)\"",
     1),
]


def apply(src_text, rules, label, report):
    out = src_text
    for i, (old, new, exp) in enumerate(rules):
        n = out.count(old)
        report.append({"label": label, "rule": i, "old_head": old.splitlines()[0][:90],
                       "expected": exp, "found": n, "ok": n == exp})
        if n != exp:
            print("[FAIL] %s rule#%d 期望 %d 处, 实得 %d 处: %r" % (label, i, exp, n, old.splitlines()[0][:90]))
            return None
        out = out.replace(old, new)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只做断言, 不写盘")
    a = ap.parse_args()
    for p in (SRC_ARM, SRC_BOTH):
        if not p.exists():
            print("[rc=3] 缺输入: %s" % p)
            return 3
    arm_src = SRC_ARM.read_text(encoding="utf-8")
    both_src = SRC_BOTH.read_text(encoding="utf-8")
    report = []
    arm_out = apply(arm_src, ARM_RULES, "arm", report)
    both_out = apply(both_src, BOTH_RULES, "both", report)
    if arm_out is None or both_out is None:
        print("[rc=2] 断言失败 ⇒ fail-closed, 未写盘")
        return 2
    # 后置机检: 派生产物里不得残留旧命名空间
    post = []
    for name, text in (("arm", arm_out), ("both", both_out)):
        for pat, exp in (("eval/rover/r487", 0), ("R487_", 0), ("--round R487", 0),
                         ("[both-r487]", 0), ("# R487 ", 0), ("2650", 0)):
            n = text.count(pat)
            post.append({"label": name, "pattern": pat, "expected": exp, "found": n, "ok": n == exp})
            if n != exp:
                print("[rc=2] 后置机检失败: %s 里 %r 出现 %d 次 (期望 %d)" % (name, pat, n, exp))
                return 2
    # 臂矩阵机检: 四臂齐全
    for tok in ("Arole)", "G)     MP=$M3B", "S)     MP=$M3B", "R)     MP=$M3B", "$ARM$TAG"):
        if tok not in arm_out:
            print("[rc=2] 臂矩阵机检失败: 缺 %r" % tok)
            return 2
    if a.check:
        print("[check] 全部断言通过 (未写盘)")
        return 0
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / "run_arm_real_r488.sh").write_text(arm_out, encoding="utf-8")
    (OUTD / "run_both_r488.sh").write_text(both_out, encoding="utf-8")
    (OUTD / "run_arm_real_r488.sh").chmod(0o755)
    (OUTD / "run_both_r488.sh").chmod(0o755)
    diff = "".join(difflib.unified_diff(arm_src.splitlines(True), arm_out.splitlines(True),
                                        "r487/run_arm_real_r487.sh", "r488/run_arm_real_r488.sh"))
    diff += "".join(difflib.unified_diff(both_src.splitlines(True), both_out.splitlines(True),
                                         "r487/run_both_r487.sh", "r488/run_both_r488.sh"))
    (OUTD / "derive_r488.diff").write_text(diff, encoding="utf-8")
    log = {
        "src_arm": str(SRC_ARM.relative_to(ROOT)), "src_both": str(SRC_BOTH.relative_to(ROOT)),
        "src_arm_sha256": hashlib.sha256(arm_src.encode()).hexdigest(),
        "src_both_sha256": hashlib.sha256(both_src.encode()).hexdigest(),
        "out_arm_sha256": hashlib.sha256(arm_out.encode()).hexdigest(),
        "out_both_sha256": hashlib.sha256(both_out.encode()).hexdigest(),
        "rules_arm": len(ARM_RULES), "rules_both": len(BOTH_RULES),
        "assertions": report + post,
        "assertions_n": len(report) + len(post),
        "failed": 0,
        "gen_ts_local": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (OUTD / "derive_r488.log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[rc=0] 派生完成: 断言 %d 条全过; arm sha256=%s both sha256=%s"
          % (log["assertions_n"], log["out_arm_sha256"][:16], log["out_both_sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
