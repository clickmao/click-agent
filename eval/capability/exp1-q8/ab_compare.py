#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-EXP1Q8 A/B: v2.3.0 (HEAD 副本) vs v2.4.0 (平行轴) —— 同语料同进程内两次 run_pass。

判据 (预注册):
  A1 细分不改判: 全量 citation 的 verdict 逐条相同 (同一语料; 键 = doc/line/pos/path)
  A2 新轴加性: v2.3.0 无 symbol_faces 字段, v2.4.0 每条有; 主判据字段一字不改
  A3 阶梯非平凡: 真实语料上 >=2 级 (G7) 且 n_symbol_faces > 0
  A4 弃权单列: 非 .cs/.py 的文件类型记 n/a_kind, 不进阶梯分母
读数为**离线复算** (与探针主链同函数), 结果落 ab_ladder_invariance.json。
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path("/home/agentuser/AgentFramework")
NEW = ROOT / "eval/capability/exp1-q4/probe_doc_ref_integrity.py"
OLD = Path("/tmp/probe_v230_head.py")
OUT = ROOT / "eval/capability/exp1-q8/ab_ladder_invariance.json"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def key(c):
    return f'{c["doc"]}|{c["doc_line"]}|{c["pos_start"]}|{c["path"]}'


m_old, m_new = load(OLD, "p230"), load(NEW, "p240")
print("versions:", getattr(m_old, "PROBE_VERSION", "2.3.0"), "->", m_new.PROBE_VERSION)
r_old = m_old.run_pass(m_old.Repo(ROOT))
r_new = m_new.run_pass(m_new.Repo(ROOT))

votes_old = {key(c): c["verdict"] for c in r_old["citations"]}
votes_new = {key(c): c["verdict"] for c in r_new["citations"]}
same_keys = set(votes_old) == set(votes_new)
diff = sorted(k for k in set(votes_old) & set(votes_new) if votes_old[k] != votes_new[k])
a1 = bool(same_keys and not diff)

has_faces_new = sum(1 for c in r_new["citations"] if c.get("symbol_faces"))
has_faces_old = sum(1 for c in r_old["citations"] if c.get("symbol_faces"))
# 主判据字段一致性 (逐条; 只比 v2.3.0 已有的键)
FIELDS = ("verdict", "resolved", "resolve_mode", "symbols_absent", "file_lines", "input_sha",
          "waive_reason", "retire_marker")
field_diff = 0
by_key_old = {key(c): c for c in r_old["citations"]}
for c in r_new["citations"]:
    o = by_key_old.get(key(c))
    if o is None:
        field_diff += 1
        continue
    for f in FIELDS:
        if o.get(f) != c.get(f):
            field_diff += 1

rungs = r_new["symbol_face_rungs"]
real_rungs = sorted(k for k in rungs if k != m_new.FACE_NA)
live_new = [c for c in r_new["citations"] if c["kind"] == "code" and not c["in_code_fence"]]
cands = [{"doc": c["doc"], "doc_line": c["doc_line"], "resolved": c["resolved"],
          "symbol": s, "rung": r, "verdict": c["verdict"]}
         for c in live_new for s, r in sorted((c.get("symbol_faces") or {}).items())
         if r in ("code_mention", "noncode_mention")]
noncode_only = [c for c in cands if c["rung"] == "noncode_mention"]
# 新候选类里, 主判据判 **ok** 的 = 旧口径「命中」而新轴显示「只在注释/字符串里」= 弱命中
weak_hits = [c for c in noncode_only if c["verdict"] == "ok"]
weak_by_file = {}
for c in weak_hits:
    weak_by_file.setdefault(c["resolved"], []).append(f'{c["symbol"]}@{c["doc"]}:{c["doc_line"]}')

reading = {
    "ab": {
        "old_version": getattr(m_old, "PROBE_VERSION", "2.3.0"), "new_version": m_new.PROBE_VERSION,
        "A1_subdivide_does_not_rejudge": a1,
        "A1_key_sets_equal": same_keys, "A1_verdict_diff_n": len(diff),
        "A1_verdict_diff_sample": diff[:10],
        "A1_existing_field_diff_n": field_diff,
        "A2_new_axis_present_old": has_faces_old, "A2_new_axis_present_new": has_faces_new,
        "n_citations_old": len(r_old["citations"]), "n_citations_new": len(r_new["citations"]),
        "verdict_counts_old": r_old["verdict_counts"], "verdict_counts_new": r_new["verdict_counts"],
        "cont_verdict_counts_old": r_old["cont_verdict_counts"],
        "cont_verdict_counts_new": r_new["cont_verdict_counts"],
        "cont_tiers_old": r_old["cont_tier_counts"], "cont_tiers_new": r_new["cont_tier_counts"],
    },
    "ladder": {
        "A3_nontrivial": len(real_rungs) >= 2 and r_new["n_symbol_faces"] > 0,
        "rungs": rungs, "real_rungs": real_rungs, "n_symbol_faces": r_new["n_symbol_faces"],
        "A4_na_kind_n": rungs.get(m_new.FACE_NA, 0),
        "n_candidates": len(cands), "n_noncode_mention": len(noncode_only),
        "n_weak_hits_verdict_ok": len(weak_hits),
        "weak_hits_by_file": {k: v for k, v in sorted(weak_by_file.items())},
    },
    "v240_v241": None,
    "corpus": {"n_docs": r_new["n_docs"], "n_inputs_fingerprinted": r_new["n_inputs_fingerprinted"]},
    "evidence_level": "L1-static (离线同进程复算, 无编译/测试/AOT)",
}
# ---- 三跑确定性: v2.4.0 存档读数 vs v2.4.1 现场读数 (只比该轴与主判据)
v240 = json.loads((ROOT / "eval/capability/exp1-q8/attribution_v240_symbol_ladder.json").read_text())
same_rungs = v240["symbol_face_rungs"] == reading_rungs if False else v240["symbol_face_rungs"] == rungs
reading["v240_v241"] = {
    "A5_ladder_rungs_identical": same_rungs,
    "A5_verdict_counts_identical": v240["citation_verdicts"] == r_new["verdict_counts"],
    "A5_cont_identical": v240["continuation_verdicts"] == r_new["cont_verdict_counts"],
    "A5_weak_hits_identical": len([c for c in v240["symbol_face_candidates"]
                                   if c["rung"] == "noncode_mention" and c["verdict"] == "ok"])
                              == len(weak_hits),
    "v240_version": v240["probe_version"], "v241_version": m_new.PROBE_VERSION,
    "v240_gate_pass": v240["gate_pass"],
}
OUT.write_text(json.dumps(reading, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(reading["ab"], ensure_ascii=False, indent=1)[:2000])
print(json.dumps({k: v for k, v in reading["ladder"].items() if k != "weak_hits_by_file"},
                 ensure_ascii=False, indent=1))
print("weak_hits files:", len(weak_by_file))
for f, v in sorted(weak_by_file.items())[:8]:
    print("  ", f, len(v), v[:4])
print("OUT:", OUT)
sys.exit(0 if (a1 and field_diff == 0 and reading["ladder"]["A3_nontrivial"]) else 2)
