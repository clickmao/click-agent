#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R614 负控有牙机检：J2b 裁选守恒判据的**真空绿封堵**两侧样例。

背景（自捕器具缺陷，R614）：R610 判据器 `eval/rover/r610/judge_r610.py` 的 J2b 实现只判
`conservation_violations == 0`，而其 `need` 串已写明「T 档有声明跑次 > 0 ∧ …」⇒ 当真机
**声明数 0**（本轮实测 9/9 跑次）时守恒式真空成立，判据报 `pass=True` = **空心绿**（把
「没测到」读成「测过通过」）。修法见该文件内的 `j2b_declared_runs > 0` 门。

本器具做三件事（零被测执行、零网络）：
  ① **源派生 + 防漂移**：从判据器源码**取**门表达式（不手抄常量）；若门被移除 ⇒ 本机检判红。
  ② **两侧样例**：声明数 0 ⇒ 必须 **不可判**（pass=False ∧ reason=NO_DECLARATION_VACUOUS）；
     声明数 > 0 且逐跑次守恒 ⇒ pass=True。
  ③ **负控有牙**：喂一条 `accepted+rejected != declared` 的合成臂 ⇒ 必须判红（violations>0）。

rc：0 = 三件全过（器具可用）｜2 = 器具缺陷（门缺失/样例不符）｜3 = 输入缺失（判据器源码不存在）。
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JUDGE = os.environ.get("J2B_TEETH_JUDGE") or os.path.join(REPO, "eval", "rover", "r610", "judge_r610.py")
OUT = os.environ.get("J2B_TEETH_OUT") or os.path.join(REPO, "eval", "rover", "r614", "j2b-teeth-r614.json")


def j2b(pass_arm_rows):
    """与判据器同语义的纯函数（入参 = 逐跑次 (declared, accepted, rejected) 列表）。"""
    declared_runs = sum(1 for d, a, j in pass_arm_rows if (d or 0) > 0)
    violations = sum(1 for d, a, j in pass_arm_rows
                     if (d or 0) > 0 and (a or 0) + (j or 0) != d)
    return {"runs_with_declaration": declared_runs, "conservation_violations": violations,
            "pass": declared_runs > 0 and violations == 0}


def main():
    if not os.path.isfile(JUDGE):
        print("INPUT_MISSING judge=%s" % JUDGE)
        return 3
    src = io.open(JUDGE, encoding="utf-8", errors="replace").read()

    # ① 源派生 + 防漂移：门表达式必须仍在源码里（取字面，不手抄）
    m = re.search(r"j2b_declared_runs\s*=\s*j2b\[[^\]]+\]\[[\"']runs_with_declaration[\"']\]", src)
    gate = re.search(r"j2b_pass\s*=\s*\(([^)]*)\)", src)
    gate_expr = gate.group(1) if gate else ""
    gate_has_declared = ("j2b_declared_runs > 0" in gate_expr)

    cases = {}
    # ② 两侧样例：真空（声明 0）⇒ 不可判；有声明且守恒 ⇒ 通过
    vac = j2b([(0, None, None), (0, None, None)])
    cases["vacuum_zero_declaration_must_not_pass"] = (vac["pass"] is False)
    ok = j2b([(3, 3, 0), (2, 1, 1)])
    cases["declared_and_conserved_must_pass"] = (ok["pass"] is True)
    # ③ 负控有牙：不守恒必须判红
    bad = j2b([(3, 1, 1)])
    cases["non_conserved_must_fail"] = (bad["pass"] is False and bad["conservation_violations"] == 1)

    defects = []
    if not (m and gate_has_declared):
        defects.append("GATE_MISSING：判据器门表达式不含 runs_with_declaration > 0（真空绿可复发）")
    for k, v in cases.items():
        if not v:
            defects.append("CASE_FAILED:%s" % k)

    res = {"instrument": os.path.relpath(JUDGE, REPO),
           "instrument_sha12": __import__("hashlib").sha256(io.open(JUDGE, "rb").read()).hexdigest()[:12],
           "gate_expr": gate_expr, "gate_source_derived": bool(m),
           "cases": cases, "vacuum_reading": vac, "negative_control": bad,
           "defects": defects, "rc": 2 if defects else 0}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"rc": res["rc"], "gate": gate_expr, "cases": cases, "defects": defects},
                     ensure_ascii=False))
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
