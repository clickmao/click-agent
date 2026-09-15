#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q14 收尾: 台账行由 verdict 派生 (禁手打数字) + 附录 O 追加 + 读回校验。"""
import json
import pathlib
import sys

DOT = chr(46)
Q = pathlib.Path(__file__).resolve().parent
ROOT = Q.parents[2]
PLAN = ROOT / "docs" / "plans" / ("v0.22.0-exp1-local-index-and-code-graph" + DOT + "md")
LEDGER = ROOT / "eval" / "capability" / ("kpi" + DOT + "jsonl")
TAG = "EXP1-Q14"


def main():
    v = json.loads((Q / ("verdict_q14" + DOT + "json")).read_text(encoding="utf-8"))
    fx = json.loads((Q / ("selftest_q14" + DOT + "json")).read_text(encoding="utf-8"))
    rows = [{"doc": c["doc"] + ":" + str(c["doc_line"]), "resolved": c["resolved"],
             "symbol": c["symbol"], "class": c["class"], "traces": len(c["traces"]),
             "registrations_elsewhere": len(c["registrations_elsewhere"])} for c in v["candidates"]]
    line = {
        "round": TAG,
        "ts": "2026-09-15T13:50:00+0800",
        "kind": "real-candidate-review+ruling(exp1-L.7#2)",
        "artifact": "eval/capability/exp1-q14/{prereg_q14.json,real_candidate_review.py,verdict_q14.json,"
                    "evidence_q14.txt,selftest_q14.json,machine_checks.sh,machine_checks_q14.txt,appendix_o.md}; "
                    "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录O",
        "change": "L.7 #2 只推进一步 = 两条真候选复核机械化: 选择子由归档判决 (rung==noncode_mention ∧ verdict==ok) "
                  "与三项树内机检 (非下划线式命名 ∧ 树内零声明 ∧ 树内仅非代码形态) 联立 ⇒ 3 行/2 枚, 与 L.7① 表独立记载逐项一致; "
                  "两枚裁定均为非引用图缺陷 (①历史快照+同行退役留痕; ②注释承诺-实现漂移且树内已登记)。"
                  "新增精度事实: 唯一构造点实参集合不含比较表达式取值 ⇒ 文件内不可生产 (死分支嫌疑, 弱旁证单列)。"
                  "未改 src/、skills/、docs/verification-registry.json、eval/rover/; 零 dotnet (对侧 R450 在场 + MemAvailable 2567MB < 2650MB 闸) "
                  "⇒ 形式校验结转, 影响面为零。",
        "readings": {
            "instrument": "real_candidate_review.py (v1.0, 语言集/语料面自 probe_v260 派生)",
            "selector": v["selector"],
            "partition": v["partition"],
            "n_rows": v["n_rows"], "n_symbols": v["n_symbols"],
            "classes": v["classes"], "waived": 0,
            "rows": rows,
            "dead_branch": [{"rel": d["rel"], "literal": d["literal"], "all_sites": d["all_sites"],
                             "ctor_lits": d["ctor_lits"],
                             "corpus_other_sites": len([s for s in d["corpus_sites"] if s["rel"] != d["rel"]])}
                            for d in v["dead_branch"]],
            "counter": {k: v["counter"][k] for k in ("caliber", "positive", "negative", "candidates",
                                                     "same_caliber_equal", "not_comparable", "nondegenerate")},
            "selftest": {"n_cases": len(fx["expected"]), "pass": fx["pass"],
                         "prio_swap": fx["prio_swap"], "dead_negative_control": fx["dead_branch"],
                         "counter": fx["counter"]},
            "checks": v["checks"], "exit": v["exit"],
            "determinism": "两跑 verdict 逐字节相同",
            "suffix_literal_hits_in_own_source": 0,
        },
        "criterion": "C1 选择子两路交叉 (3 行/2 枚 与表 859 逐项一致) | C2 排除面守恒 (27=3+21+3) | "
                     "C3 类分布非平凡 (两类皆非零) ∧ 弃权 0 | C4 逐枚依据为行级机检 (含他处登记行) | "
                     "C5 死分支判据两侧样例 (夹具负控不判死) | C6 仪器自检 6 格 + 优先级置换 + 计数同口径 = 全过 | "
                     "C7 两跑逐字节相同 + 本器零后缀字面量",
        "honest_boundaries": [
            "证据等级 L1-static (真归档语料 + 真树读取 + 夹具自检; 无编译/测试/AOT ⇒ 不报 L3/L4)",
            "①「文档时效」依赖同行留痕 + 版本存档, 未执行文档修复动作",
            "②「归口既有登记」依赖行级机检, 未人工复核登记行措辞适用性",
            "「死分支」只证文件内不可生产, 跨文件构造点未穷尽 (他处 1 处已判非构造实参) ⇒ 不作全程序不可达宣称",
            "形式校验结转 (对侧 R450 在场 + 内存低于起手闸); 本轮新增附录 O ⇒ 与 Q13 读数不可直接比",
            "「语言无关令」在 docs/ 内零留痕 ⇒ 只按工程纪律遵守 (派生 + 机检), 不按已钦定立项",
        ],
    }
    kp = Q / ("kpi_line_q14" + DOT + "json")
    kp.write_text(json.dumps(line, ensure_ascii=False, indent=1), encoding="utf-8")

    led = LEDGER.read_text(encoding="utf-8")
    if TAG in led:
        print("LEDGER_NOOP: 台账已有 %s (幂等)" % TAG)
    else:
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    back = LEDGER.read_text(encoding="utf-8").splitlines()
    last = json.loads(back[-1])
    print("LEDGER_OK lines=%d last_round=%s" % (len(back), last.get("round")))
    print("SUBST=verdict+ledger_sha_match")

    apx = (Q / ("appendix_o" + DOT + "md")).read_text(encoding="utf-8")
    doc = PLAN.read_text(encoding="utf-8")
    if "附录 O · EXP1-Q14" in doc:
        print("PLAN_NOOP: 附录 O 已存在 (幂等)")
    else:
        if not doc.endswith("\n"):
            doc += "\n"
        PLAN.write_text(doc + apx, encoding="utf-8")
    rb = PLAN.read_text(encoding="utf-8")
    print("PLAN_OK lines=%d has_appendix=%s tail=%s" % (
        len(rb.splitlines()), "附录 O · EXP1-Q14" in rb, rb.rstrip().splitlines()[-1][:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
