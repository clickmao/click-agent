#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R497 候选④ 器具↔产品逐位比对 (gate rules 双实现)。

产品侧 = C# TurnGateJudge (LocalGenerationPort.cs, 源码);
器具侧 = eval/rover/r468/gate_rules.py (从 C# 源码**派生**标记/白名单, 不是手抄)。
本脚本把 R497 单测里的 InlineData 正/负控逐条喂给器具侧, 断言两实现同判;
并断言白名单字符集**逐字节未变** (R497 只加标记, 不动白名单)。

用法: python3 gate_port_parity_r497.py [--out gate-parity-r497.json]
退出码: 0 = 双实现一致; 1 = 有红
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R468 = os.path.join(ROOT, "eval/rover/r468")
TESTS = os.path.join(ROOT, "src/agent.tests/R497FingerprintAndSynonymTests.cs")
GATE = os.path.join(ROOT, "src/agent.modelqueue/LocalGenerationPort.cs")
NEW_MARKERS = ["复述一次", "说一遍", "讲一遍", "念一遍"]
R465_CHARS = "再讲遍次重复述从头说要你上面那条这句话的来回新下念看给把一吧哦嗯啊呀啦哇"

sys.path.insert(0, R468)
import gate_rules as gr  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="gate-parity-r497.json")
    a = ap.parse_args()
    red, rows = [], []
    src = open(TESTS, encoding="utf-8").read()
    cases = gr._inline_cases(src, "R497D_SynonymRepeat_Face")
    for msg, exp in cases:
        got = gr.is_pure_repeat(msg)
        cls = gr.classify(msg)
        ok = (got == exp)
        rows.append({"method": "IsPureRepeat", "msg": msg, "expect": exp, "port": got, "port_classify": cls, "ok": ok})
        if not ok:
            red.append("双实现不一致 (IsPureRepeat): %r 期望 %s / 器具 %s" % (msg, exp, got))
    # 优先级铁律面: 产品口径 = 机械放行先于复述吸收 ⇒ 吸收 = (!MechanicalPass && IsPureRepeat)
    abs_rows = gr._inline_cases(src, "R497D_AbsorbedFace_MechanicalPassWins")
    for msg, exp in abs_rows:
        got = (not gr.mechanical_pass(msg)) and gr.is_pure_repeat(msg)
        cls = gr.classify(msg)
        want_cls = "repeat" if exp else cls
        ok = (got == exp) and (cls == want_cls)
        rows.append({"method": "AbsorbedFace", "msg": msg, "expect": exp, "port": got, "port_classify": cls, "ok": ok})
        if not ok:
            red.append("双实现不一致 (吸收面): %r 期望吸收=%s 器具=%s (classify=%s)" % (msg, exp, got, cls))
    for mk in NEW_MARKERS:
        if mk not in gr.REPEAT_MARKERS:
            red.append("新标记 %r 未进器具 REPEAT_MARKERS" % mk)
    if gr.REPEAT_CHARS != R465_CHARS:
        red.append("白名单字符集已漂移: %r" % gr.REPEAT_CHARS)
    meta = dict(gr.RULES_META)
    rep = {"round": "R497", "instrument": "gate_port_parity_r497.py", "cases": len(rows),
           "rows": rows, "new_markers": NEW_MARKERS, "port_markers_n": len(gr.REPEAT_MARKERS),
           "port_meta": meta, "red": red, "verdict": "GREEN" if not red else "RED"}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("[gate_parity] 用例 %d, 器具标记 %d 条, verdict=%s" % (len(rows), len(gr.REPEAT_MARKERS), rep["verdict"]))
    print("  器具台账: gate_src_sha256=%s" % str(meta.get("gate_source_sha256", ""))[:16])
    for r in rows:
        print("   %-11s %-22s expect=%-5s port=%-5s classify=%-6s %s"
              % (r["method"], r["msg"], r["expect"], r["port"], r["port_classify"], "ok" if r["ok"] else "RED"))
    for x in red:
        print("  [RED] " + x)
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
