#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q10 A/B: v2.5.0 vs v2.6.0 零回归 + 细分轴守恒/非平凡 + 与 Q9 用户面口径的机检对账。

预注册判据 C1/C2/C3/C6 的机器判定:
  C1 加性零回归: 旧轴读数逐位相同 (verdict/边强/子级/live 数/弱边清单旧字段), 新字段只出现在 v2.6.0
  C2 守恒: Σ kind(弱边) == #弱边 == len(edge_weak_list)
  C3 非平凡: 真语料 kind 分布 >= 2 类
  C6 口径对账: 用 Q9 表 (name_shape, n_declared_elsewhere) 机检「虚增 20 条 = 62 弱边的 32%」之说
  P1/P4 预测检验: 边级 named_fact < 20 ; 符号级 named_fact == 20 (符号集 = Q9 A 集口径)
退出码: 0 全过 / 2 判据失败 / 3 测量或环境失败 (三态, 与器具同口径)
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
Q9 = HERE.parent / "exp1-q9"
OLD_KEYS = ("verdict_counts", "edge_strength_counts", "edge_sublevel_counts",
            "n_citations_code_live", "n_docs", "n_edges_strong_with_weak_symbols",
            "symbol_face_rungs", "cont_verdict_counts", "cont_tier_counts")
NEW_KEYS = ("edge_kind_counts", "weak_symbol_kind_counts", "n_weak_edges",
            "n_weak_symbols_classified", "kind_conserved")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sym_cls_of(a: dict) -> str:
    """由 Q9 A 表**自身记录的字段**推出类 (与器具规则同序): cross_file > named_fact > comment_only。"""
    if (a.get("n_declared_elsewhere") or 0) >= 1:
        return "cross_file"
    if a.get("name_shape") in ("snake_case", "SCREAMING_SNAKE"):
        return "named_fact"
    return "comment_only"


def run(probe: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "probe_out.json"
    cmd = [sys.executable, str(probe), "--repo", str(REPO), "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    (out_dir / "stdout.txt").write_text(p.stdout, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(p.stderr, encoding="utf-8")
    if not out.is_file():
        return None, p.returncode, {"stage": "no_output", "stderr_tail": p.stderr[-400:]}
    return json.loads(out.read_text(encoding="utf-8")), p.returncode, {}


def main():
    res = {"round": "EXP1-Q10", "repo": str(REPO), "checks": {}, "predictions": {}}
    r_old, rc_old, e_old = run(Q9 / "probe_v250.py", HERE / "ab" / "run250")
    r_new, rc_new, e_new = run(HERE / "probe_v260.py", HERE / "ab" / "run260")
    res["exit_codes"] = {"v250": rc_old, "v260": rc_new}
    res["stderr"] = {"v250": e_old, "v260": e_new}
    if r_old is None or r_new is None:
        res["verdict"] = "MEASUREMENT_FAILED"
        (HERE / "ab_kind.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"stage": "ab", "verdict": res["verdict"], "exit_code": 3}, ensure_ascii=False))
        return 3

    # ---- C1 加性零回归 (逐键逐位)
    diff = {}
    for k in OLD_KEYS:
        if json.dumps(r_old.get(k), sort_keys=True, ensure_ascii=False) != \
           json.dumps(r_new.get(k), sort_keys=True, ensure_ascii=False):
            diff[k] = {"v250": r_old.get(k), "v260": r_new.get(k)}
    # 旧弱边清单只比较 v2.5.0 时代就存在的字段
    old_sub = [{kk: vv for kk, vv in e.items()
                if kk not in ("edge_kind", "kind_reason", "kind_per_symbol")}
               for e in r_old.get("edge_weak_list", [])]
    new_sub = [{kk: vv for kk, vv in e.items()
                if kk not in ("edge_kind", "kind_reason", "kind_per_symbol")}
               for e in r_new.get("edge_weak_list", [])]
    weak_list_same = (json.dumps(old_sub, sort_keys=True, ensure_ascii=False)
                      == json.dumps(new_sub, sort_keys=True, ensure_ascii=False))
    new_only = [k for k in NEW_KEYS if k not in r_old]
    new_keys_visible = all(k in r_new for k in NEW_KEYS)
    res["checks"]["C1_old_axis_identical"] = {"pass": not diff and weak_list_same,
                                              "differing_keys": sorted(diff),
                                              "weak_list_identical_old_fields": weak_list_same}
    res["checks"]["C1_additive_new_fields"] = {"pass": len(new_only) == len(NEW_KEYS) and new_keys_visible,
                                               "absent_in_v250": new_only,
                                               "present_in_v260": new_keys_visible}
    res["old_axis_counts"] = {k: r_new.get(k) for k in OLD_KEYS}

    # ---- C2/C3 守恒与非平凡
    kc = r_new.get("edge_kind_counts") or {}
    n_weak = r_new.get("n_weak_edges")
    res["checks"]["C2_conservation"] = {"pass": bool(sum(kc.values()) == n_weak
                                                     == len(r_new.get("edge_weak_list", []))),
                                        "sum_kind": sum(kc.values()), "n_weak_edges": n_weak,
                                        "len_weak_list": len(r_new.get("edge_weak_list", []))}
    res["checks"]["C3_nontrivial"] = {"pass": len(kc) >= 2, "n_kinds": len(kc)}

    # ---- C6 与 Q9 用户面口径对账 (符号级 vs 边级)
    q9 = json.loads((Q9 / "weak_edge_table.json").read_text(encoding="utf-8"))
    A = q9["set_A_symbol_level"]
    sym_cls = Counter()
    for a in A:
        sym_cls[sym_cls_of(a)] += 1
    res["q9_caliber"] = {
        "A_table_n": len(A),
        "A_table_rule_classes": dict(sym_cls),
        "q9_prose_claim": "20 条名字类事实 (= 62 条弱边的 32%)",
        "instrument_symbol_kind_counts": r_new.get("weak_symbol_kind_counts"),
        "instrument_edge_kind_counts": kc,
        "unit_note": "A 表 = 符号级; edge_kind_counts = 引用级边 ⇒ 两口径不可换算",
    }
    prose_named_fact, prose_edges = 20, 62
    edge_named_fact = kc.get("named_fact", 0)
    res["checks"]["C6_doc_caliber_reconciliation"] = {
        "pass": edge_named_fact != prose_named_fact,   # 判据: 若边级 == 20 则换算成立(无需修文档)
        "edge_level_named_fact": edge_named_fact,
        "prose_claim_edges": prose_named_fact,
        "symbol_level_named_fact_from_A_table": sym_cls["named_fact"],
        "verdict": ("prose 换算不成立 ⇒ 计划文档必须改成符号级/边级两个数"
                    if edge_named_fact != prose_named_fact else "prose 换算成立"),
    }

    # ---- 预测检验 (预注册)
    res["predictions"]["P1_edge_named_fact_lt_20"] = {
        "pass": edge_named_fact < 20, "observed": edge_named_fact}
    res["predictions"]["P2_edge_kinds_ge_3"] = {"pass": len(kc) >= 3, "observed": len(kc)}
    res["predictions"]["P3_edge_cross_file_ge_1"] = {
        "pass": kc.get("cross_file", 0) >= 1, "observed": kc.get("cross_file", 0)}
    res["predictions"]["P4_symbol_named_fact_eq_20"] = {
        "pass": (r_new.get("weak_symbol_kind_counts") or {}).get("named_fact") == 20,
        "observed": (r_new.get("weak_symbol_kind_counts") or {}).get("named_fact"),
        "note": "符号集口径 = 弱边内的 *_mention 符号; 若不等先查是否与 Q9 的 A 集(noncode∧ok)同口径"}
    res["predictions"]["P5_zero_regression"] = {"pass": res["checks"]["C1_old_axis_identical"]["pass"]}

    # ---- 事后对账 (checks_posthoc): P4 判否 ⇒ 先排除「分母口径不同」, 不得直接宣称 Q9 错
    # 缺陷记录 (Q10 自捕, instrument_defect_q10_v1): 首版此处读 r_new["citations"] —— attribution JSON
    # **不含** citations 键 (全量引用只落 citations.jsonl) ⇒ 读到 0 条/空分布, 而判定照旧「通过」。
    # 这正是「空心仪器」形态 (恒定空值冒充读数) ⇒ 改为读落盘的 citations.jsonl, 并加**非空硬闸**:
    # 引用数为 0 ⇒ 判测量失败 (exit 3), 不得静默产出空分布。
    run260_cites = HERE / "ab" / "run260" / "citations.jsonl"
    cites_new = ([json.loads(x) for x in run260_cites.read_text(encoding="utf-8").splitlines() if x.strip()]
                 if run260_cites.is_file() else [])
    if not cites_new:
        res["checks_posthoc"] = {"instrument_defect_q10_v1": "citations.jsonl 为空/缺失 ⇒ 测量失败",
                                 "A_caliber_cites_n": 0}
        res["verdict"] = "MEASUREMENT_FAILED"
        (HERE / "ab_kind.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"stage": "posthoc", "verdict": res["verdict"],
                          "reason": "citations.jsonl empty/missing", "exit_code": 3}, ensure_ascii=False))
        return 3
    a_cal = Counter()
    n_a_cal = 0
    a_cal_strong = Counter()
    n_a_strong = 0
    for c in cites_new:
        if c.get("verdict") != "ok":
            continue
        for p in (c.get("kind_per_symbol") or []):
            if p["rung"] != "noncode_mention":
                continue
            if c.get("edge_strength") == "weak":
                n_a_cal += 1
                a_cal[p["symbol_kind"]] += 1
            elif c.get("edge_strength") == "strong":
                n_a_strong += 1
                a_cal_strong[p["symbol_kind"]] += 1
    combined = Counter(a_cal)
    combined.update(a_cal_strong)
    q9_match = (dict(combined) == dict(sym_cls)) and ((n_a_cal + n_a_strong) == len(A))
    res["checks_posthoc"] = {
        "A_caliber_symbol_kind_counts": dict(a_cal),
        "A_caliber_n": n_a_cal,
        "q9_A_table_rule_classes": dict(sym_cls),
        "q9_A_table_n": len(A),
        "caliber_note": ("A 口径 = 弱边内 noncode_mention ∧ verdict==ok 的符号; "
                         "P4 的分母是 weak_symbol_kind_counts (含 code_mention, 全 90 枚) "
                         "⇒ 两数不可直接比 (P4 判否是**分母口径**差异, 不是规则不一致)"),
        "match_with_q9_table": dict(a_cal) == dict(sym_cls),
        "A_caliber_strong_edge_symbol_kind_counts": dict(a_cal_strong),
        "A_caliber_strong_edge_n": n_a_strong,
        "A_caliber_combined_counts": dict(combined),
        "A_caliber_combined_n": n_a_cal + n_a_strong,
        "match_with_q9_table_combined": q9_match,
        "gap_explanation": ("A 表 25 枚 = 弱边内 noncode∧ok (A1) + **强边里混的** noncode∧ok (A2, "
                            "被边级「最强胜」聚合吞掉) ⇒ 单看弱边会少算 A2 枚; "
                            "边级与符号级的差 = 单位差 + 混强边遮蔽, 两者都要显式"),
        "corpus_drift_note": ("A 表产出于 Q9 轮; 本轮 n_weak_edges=%s (Q9 记录 62) ⇒ 语料是移动目标, "
                              "逐类差值须先扣语料漂移再谈规则差异" % r_new.get("n_weak_edges")),
        "instrument_defect_q10_v1": ("首版事后对账读 attribution JSON 的 citations 键 (不存在) ⇒ 空分布"
                                     "而判定照旧通过 (空心仪器形态); 已改为读 citations.jsonl + 非空硬闸"),
    }
    res["checks"]["C6_doc_caliber_reconciliation"]["A_caliber_named_fact"] = a_cal.get("named_fact")
    res["checks"]["C6_doc_caliber_reconciliation"]["A_caliber_matches_q9_table"] = (
        dict(a_cal) == dict(sym_cls))

    # ---- 事后对账② (drift-immune): 逐项比对 Q9 A 表的 (符号, 被引文件) 对
    # 计数级对比会被**语料漂移**污染 (Q9 之后新增报告文档 ⇒ 新引用/新符号) ⇒ 改用逐项一致率:
    # 只看 Q9 A 表自己那 25 项在当前仪器下被判成什么类, 与 A 表字段推出的类逐项比。
    instr_pairs = {}
    for c in cites_new:
        if c.get("verdict") != "ok":
            continue
        for p in (c.get("kind_per_symbol") or []):
            if p["rung"] != "noncode_mention":
                continue
            instr_pairs[(p["symbol"], c.get("resolved"))] = {
                "kind": p["symbol_kind"], "shape": p["shape"],
                "declared_elsewhere": p["declared_elsewhere"],
                "edge": c.get("edge_strength"), "doc": c.get("doc"), "doc_line": c.get("doc_line")}
    agree, conflict, q9_only = [], [], []
    for a in A:
        key = (a["symbol"], a.get("resolved"))
        want = sym_cls_of(a)
        got = instr_pairs.get(key)
        if got is None:
            q9_only.append({"key": list(key), "q9_class": want})
        elif got["kind"] == want:
            agree.append({"key": list(key), "kind": want, "edge": got["edge"]})
        else:
            conflict.append({"key": list(key), "q9_class": want, "instrument": got})
    res["checks_posthoc"]["item_level_agreement"] = {
        "n_q9_items": len(A),
        "n_agree": len(agree),
        "n_conflict": len(conflict),
        "n_q9_only_missing_now": len(q9_only),
        "conflicts": conflict[:10],
        "q9_only": q9_only[:10],
        "instr_only_extra_pairs": [list(k) for k in instr_pairs
                                   if k not in {(a["symbol"], a.get("resolved")) for a in A}][:10],
        "verdict": ("逐项全部一致 ⇒ 规则与 Q9 表格字段同口径 (计数差全部来自语料漂移)"
                    if not conflict else "存在逐项冲突 ⇒ 规则或口径确有分歧, 需逐条复核"),
    }

    crit_pass = all(res["checks"][k]["pass"] for k in
                    ("C1_old_axis_identical", "C1_additive_new_fields", "C2_conservation", "C3_nontrivial"))
    res["criteria_all_pass"] = crit_pass
    res["predictions_all_pass"] = all(v["pass"] for v in res["predictions"].values())
    res["verdict"] = ("CRITERIA_PASS" if crit_pass else "CRITERIA_FAIL")
    res["probe_sha256"] = {"v250": sha_file(Q9 / "probe_v250.py"), "v260": sha_file(HERE / "probe_v260.py")}
    (HERE / "ab_kind.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": res["verdict"],
        "criteria": {k: res["checks"][k]["pass"] for k in res["checks"]},
        "predictions": {k: v["pass"] for k, v in res["predictions"].items()},
        "edge_kind_counts": kc,
        "weak_symbol_kind_counts": r_new.get("weak_symbol_kind_counts"),
        "n_weak_edges": n_weak,
        "q9_A_rule_classes": dict(sym_cls),
        "A_caliber_symbol_kind_counts": res["checks_posthoc"]["A_caliber_symbol_kind_counts"],
        "A_caliber_combined_counts": res["checks_posthoc"]["A_caliber_combined_counts"],
        "match_q9_A_table": res["checks_posthoc"]["match_with_q9_table"],
        "match_q9_A_table_combined": res["checks_posthoc"]["match_with_q9_table_combined"],
        "item_level_agreement": {k: res["checks_posthoc"]["item_level_agreement"][k]
                                 for k in ("n_q9_items", "n_agree", "n_conflict",
                                           "n_q9_only_missing_now", "verdict")},
        "exit_code": 0 if crit_pass else 2,
    }, ensure_ascii=False, indent=2))
    return 0 if crit_pass else 2


if __name__ == "__main__":
    sys.exit(main())
