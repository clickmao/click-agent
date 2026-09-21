#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R617 前缀不变量机检（派生自 eval/rover/r615/prefix-r615.json 的生成口径，禁手抄数字）：

口径（承 R615 的自捕修法）：**按前缀字节切块** —— 尾块 = `<action_candidates>` 起至 `</action_candidates>` 止
（raw 源码里的 `\\uXXXX` 转义在前缀内是 1 字符，按源码字面长算会误判 append_only）。

判据（三条，缺一即 rc=1）：
  ① 只加厚：chars(T) ≥ chars(C_anchor) ∧ 新块前的字符逐位不变 ∧ 尾块后收尾逐位不变；
  ② 三档互异：T / r615 / legacy 三个 sha 两两不同（否则轴未生效 ⇒ 臂对称不成立）；
  ③ 轴锚逐位：r615 档 == R615 冻结 pin、legacy 档 == R610–R614 冻结 pin（由 git 侧的生成物常量复核）。

用法: python3 eval/rover/r617/prefix_r617.py [--out eval/rover/r617/prefix-r617.json]
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
R615_PIN = "8b8be6b8070e92a9d5d5bef697759c186c93b8ccafe47d55540b3393d95d351b"
LEGACY_PIN = "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e"
GEN_CHARS_MIN = 14863          # PrefixMinCharsForCache97（只许加厚下限）


def sha12(p: str) -> str:
    return hashlib.sha256(io.open(os.path.join(REPO, p), "rb").read()).hexdigest()[:12]


def block_parts(pre: str):
    i = pre.index("<action_candidates>")
    j = pre.index("</action_candidates>") + len("</action_candidates>")
    return pre[:i], pre[i:j], pre[j:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r617/prefix-r617.json"))
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(REPO, "tools/r1gen"))
    import r1prompt  # noqa: E402

    cur, r615, legacy = r1prompt.PREFIX, r1prompt.PREFIX_R615, r1prompt.PREFIX_LEGACY
    cp, cb, cs = block_parts(cur)
    op, ob, os_ = block_parts(r615)
    lp, lb, ls = block_parts(legacy)
    shas = {"T": r1prompt.prefix_sha(), "r615": r1prompt.prefix_sha_r615(),
            "legacy": r1prompt.prefix_sha_legacy()}
    checks = {
        "append_only": bool(len(cur) >= len(r615) and cp == op and cs == os_),
        "three_axes_distinct": bool(len(set(shas.values())) == 3),
        "anchors_verbatim": bool(shas["r615"] == R615_PIN and shas["legacy"] == LEGACY_PIN),
        "min_chars_gate": bool(len(cur) >= GEN_CHARS_MIN),
        "tail_block_replaced": bool(cb != ob),
    }
    rc = 0 if all(checks.values()) else 1
    doc = {
        "round": "R617",
        "instrument": "tools/r1gen/r1prompt.py + tools/r1gen/gen_csharp.py",
        "source_sha12": {"tools/r1gen/r1prompt.py": sha12("tools/r1gen/r1prompt.py"),
                         "tools/r1gen/gen_csharp.py": sha12("tools/r1gen/gen_csharp.py"),
                         "src/agent/contract/StructuredPrompt.cs": sha12("src/agent/contract/StructuredPrompt.cs")},
        "pin_current": {"chars": len(cur), "sha256": shas["T"],
                        "role": "产品新缺省（R617 尾块：豁免句 → 「执行面只读本字段」必声明句）"},
        "pin_r615_anchor": {"chars": len(r615), "sha256": shas["r615"],
                            "role": "R617 对照臂锚 = R615 现盘块（逐字节，由 git show HEAD 派生）"},
        "pin_legacy_anchor": {"chars": len(legacy), "sha256": shas["legacy"],
                              "role": "第二锚 = R610–R614 冻结 pin（保轴历史档可复现）"},
        "block_analysis": {"block_start_old": len(op), "block_start_new": len(cp),
                           "identical_before_block_start": cp == op,
                           "block_chars_old": len(ob), "block_chars_new": len(cb),
                           "suffix_after_block_identical": cs == os_,
                           "delta_chars": len(cur) - len(r615)},
        "checks": checks,
        "verdict": {"rc": rc, "label": "PASS（只加厚 ∧ 三档互异 ∧ 双锚逐位）" if rc == 0 else "FAIL"},
        "honest_bounds": [
            "本件只证**前缀结构与轴锚**；不证任何质量/成本收益（收益面在真机臂）",
            "尾块措辞是唯一被测自由度；到达面遥测（R1Transcript）为器具，两臂同开",
            "跨轮禁相减：R615 pin 与 R617 pin 并列，不相减",
        ],
        "written_at": None,
    }
    json.dump(doc, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "chars": len(cur), "sha256": shas["T"][:16],
                      "r615": shas["r615"][:16], "legacy": shas["legacy"][:16],
                      "checks": checks}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
