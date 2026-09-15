#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q9 A/B: v2.4.1 vs v2.5.0 边强轴「细分不改判 + 纯加性 + 守恒」+ 确定性两跑。

判据 (prereg_q9.json B1/B2/B3/B5):
  B1 逐条 citation verdict 完全相同 ∧ 旧版既有字段逐条逐键相同
  B2 旧版侧不存在任何 edge_* 字段 (纯加性)
  B3 边强计数之和 == live 代码引用数 ∧ n_citations_total 与旧版相同
  B5 同语料两跑, 边强分布与逐条 edge 字段逐位相同 (确定性)
出口码: 0 全过 / 2 断言失败 / 3 测量或环境失败 (三态分离, 不与断言失败同码)
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NEW_FIELDS = ("edge_strength", "edge_sublevel", "edge_weak_symbols", "edge_broken_symbols")


def load(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main():
    try:
        v241 = load("probe_v241", ROOT / "eval/capability/exp1-q4/probe_doc_ref_integrity.py")
        v250 = load("probe_v250", HERE / "probe_v250.py")
    except Exception as exc:  # 环境/测量失败
        print(json.dumps({"error": repr(exc), "stage": "load", "exit_code": 3}, ensure_ascii=False))
        return 3
    try:
        old = v241.run_pass(v241.Repo(ROOT))
        new = v250.run_pass(v250.Repo(ROOT))
        new2 = v250.run_pass(v250.Repo(ROOT))
    except Exception as exc:
        print(json.dumps({"error": repr(exc), "stage": "run_pass", "exit_code": 3}, ensure_ascii=False))
        return 3

    o, n = old["citations"], new["citations"]
    ident_o = [(c["doc"], c["doc_line"], c["path"], c["kind"], c["line_start"], c["line_end"]) for c in o]
    ident_n = [(c["doc"], c["doc_line"], c["path"], c["kind"], c["line_start"], c["line_end"]) for c in n]
    if ident_o != ident_n:
        print(json.dumps({"stage": "align", "error": "citation_identity_sequence_differs",
                          "n_old": len(o), "n_new": len(n), "exit_code": 3}, ensure_ascii=False))
        return 3

    verdict_diff = [(a["doc"], a["doc_line"], a["verdict"], b["verdict"])
                    for a, b in zip(o, n) if a["verdict"] != b["verdict"]]
    field_diff = {}
    for a, b in zip(o, n):
        for k, v in a.items():
            if k in NEW_FIELDS or k == "verdict":
                continue
            if k not in b or b[k] != v:
                field_diff.setdefault(k, []).append((a["doc"], a["doc_line"]))
    old_has_new = [(a["doc"], a["doc_line"], k) for k in NEW_FIELDS for a in o if k in a]
    live = [c for c in n if c["kind"] == "code" and not c["in_code_fence"]]
    edge_on_live = [c for c in live if "edge_strength" in c]
    edge_on_nonlive = [(c["doc"], c["doc_line"], c["verdict"]) for c in n
                       if ("edge_strength" in c) and (c["kind"] != "code" or c["in_code_fence"])]

    def edge_sig(r):
        return sorted((c["doc"], c["doc_line"], c["path"], c.get("edge_strength"),
                       c.get("edge_sublevel"), c.get("edge_weak_symbols"),
                       c.get("edge_broken_symbols")) for c in r["citations"]
                      if c.get("edge_strength"))

    det_edges = edge_sig(new) == edge_sig(new2)
    det_counts = new["edge_strength_counts"] == new2["edge_strength_counts"]
    sum_conserved = sum(new["edge_strength_counts"].values()) == new["n_citations_code_live"]

    checks = {
        "B1_verdict_diff_zero": len(verdict_diff) == 0,
        "B1_shared_fields_identical": len(field_diff) == 0,
        "B2_purely_additive": len(old_has_new) == 0 and len(edge_on_live) > 0
                              and len(edge_on_nonlive) == 0,
        "B3_conservation": sum_conserved and new["n_citations_total"] == old["n_citations_total"]
                           and new["verdict_counts"] == old["verdict_counts"],
        "B4_nontrivial_on_corpus": new["edge_levels_nontrivial"],
        "B5_determinism_edges": det_edges and det_counts,
    }
    out = {
        "n_citations": {"v241": len(o), "v250": len(n)},
        "verdict_counts": {"v241": old["verdict_counts"], "v250": new["verdict_counts"]},
        "edge_strength_counts": new["edge_strength_counts"],
        "edge_sublevel_counts": new["edge_sublevel_counts"],
        "n_edges_strong_with_weak_symbols": new["n_edges_strong_with_weak_symbols"],
        "verdict_diff_n": len(verdict_diff), "verdict_diff_examples": verdict_diff[:5],
        "shared_field_diff": {k: {"n": len(v), "examples": v[:3]} for k, v in field_diff.items()},
        "old_side_has_new_fields_n": len(old_has_new),
        "edges_on_live_n": len(edge_on_live), "edges_on_nonlive_n": len(edge_on_nonlive),
        "checks": checks, "all_pass": all(checks.values()), "exit_code": 0 if all(checks.values()) else 2,
    }
    (HERE / "ab_edges.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
