#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幂等追加 EXP1-Q2 的 KPI 台账行 (与 exp1-q1/q3 行同 schema; 已存在则跳过)。

纪律: 读数必须落 eval/capability/kpi.jsonl; 同类运行只追加一次 (按 round+step 去重)。
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
KPI = REPO / "eval" / "capability" / "kpi.jsonl"
RESULT = REPO / "eval" / "capability" / "exp1-q2" / "result.json"
SELFTEST = REPO / "eval" / "capability" / "exp1-q2" / "selftest_result.json"

ROUND, STEP = "EXP1-Q2", "exp1-q2-contract-premise-and-doc-ref-integrity"


def main():
    if not RESULT.is_file():
        print(json.dumps({"error": "missing result.json", "exit_code": 3}, ensure_ascii=False))
        return 3
    r = json.loads(RESULT.read_text(encoding="utf-8"))
    st = json.loads(SELFTEST.read_text(encoding="utf-8"))["summary"] if SELFTEST.is_file() else {}
    tz = timezone(timedelta(hours=8))
    ts = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")

    readings = {
        "gate_pass": r["gate_pass"],
        "exit_code": r["exit_code"],
        "evidence_level": r["evidence_level"],
        "instrument_revision": r["probe_version"],
        "selftest_checks": st.get("n_checks"),
        "selftest_failed": st.get("n_failed"),
        "gates": {k: v for k, v in r["gates"].items() if isinstance(v, bool)},
        "citation_verdicts": r["citation_verdicts"],
        "waive_reasons": r["waive_reasons"],
        "stale_path_n": r["citation_verdicts"].get("stale_path", 0),
        "relocated_n": r.get("relocated_n", 0),
        "relocated_fact_verdicts": r.get("relocated_fact_verdicts", {}),
        "symbol_counts": r["symbol_occurrences"],
        "n_docs": r["corpus"]["n_docs"],
        "n_inputs_fingerprinted": r["corpus"].get("n_inputs_fingerprinted"),
        "q2_decision_data": {k: v for k, v in r["q2_decision_data"].items()
                             if not isinstance(v, list)},
        "instrument_defects_found": ["v1_bare_filename_judged_stale_path(389 inflated)",
                                     "v2_deleted_vs_relocated_not_separated",
                                     "selftest_caught_missing_repo_judged_red(should abstain)"],
        "form_check_deferred": "peer editing src/agent.roles/CorrectionDetector.cs (mtime<5min) => dotnet not run (3rd carry-over)",
        "next_candidate": "§1.2/§1.3 引用事实定点修复 (8 真删 + 21 搬家改注/改路径)",
    }

    rec = {
        "kind": "task-step",
        "branch": "tasks",
        "round": ROUND,
        "step": STEP,
        "ts": ts,
        "plan_item": ("docs/plans/v0.22.0-exp1-local-index-and-code-graph.md §8-Q2（最前未完成计划项 exp1，只推进一步："
                      "把 Q2「是否引入 manifest + schema_version」从判断题变数据题，并先做前提核验）"),
        "modification": ("新增器具 eval/capability/exp1-q2/{probe_doc_ref_integrity.py(v2.1.0),"
                         "selftest_doc_ref_integrity.py(21 项自证, 含 CLI 端到端回放)} + result.json/citations.jsonl/"
                         "selftest_result.json/git_deletion_evidence.txt/probe_stdout.txt + 计划文档 附录D/§1.2 校正块/"
                         "§1.3 校正块/§4.4 前提证伪块/§8-Q2 行。零产品源码改动、零 dotnet（避让对侧 30m 作业在改产品源码）。"
                         "仪器修两处：v1 裸文件名误判 stale_path（389 虚高）⇒ 三级归属+弃权；v2 未区分删除/搬家 ⇒ 第四级 relocated。"),
        "readings": json.dumps(readings, ensure_ascii=False),
        "evidence": ("eval/capability/exp1-q2/result.json; eval/capability/exp1-q2/selftest_result.json; "
                     "eval/capability/exp1-q2/citations.jsonl; eval/capability/exp1-q2/git_deletion_evidence.txt; "
                     "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md#附录D"),
    }

    existing = []
    if KPI.is_file():
        for line in KPI.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line:
                existing.append(json.loads(line))
    if any(e.get("round") == ROUND and e.get("step") == STEP for e in existing):
        print(json.dumps({"status": "already_present", "round": ROUND, "n_lines": len(existing)},
                         ensure_ascii=False))
        return 0
    with KPI.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    after = [l for l in KPI.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    print(json.dumps({"status": "appended", "round": ROUND, "n_lines_before": len(existing),
                      "n_lines_after": len(after),
                      "verify_last_round": json.loads(after[-1])["round"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
