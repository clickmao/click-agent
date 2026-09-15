#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q11 · `other` 桶分布先行分解器 (边级, 只读已落盘字段)

用途: 回答「v2.6.0 边级 kind 轴里 `other` 桶 (17 边) 是不是同质 catch-all? 细分是否有据?」
纪律: 不修改 v2.6.0 仪器; 不做 AST; 不新增语料根; 不改判任何 verdict; 只读 citations.jsonl。
判据: 全部取自同目录 prereg_q11.json (写盘时刻早于本文件输出)。

退出码: 0 = 判据全过 / 2 = 判据失败(真红) / 3 = 测量或环境失败(弃权)
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys, collections

PREREG_VERSION = "q11.1"

CLASSES = ["target_non_cs", "target_unresolved", "mixed_rung",
           "pure_code_mention", "other_residual"]
PRECEDENCE = ["target_non_cs", "target_unresolved", "mixed_rung",
              "pure_code_mention", "other_residual"]
CS_EXT = ".cs"


def classify(rec: dict, precedence=PRECEDENCE) -> str:
    """边级分类 (顺序预注册)。只读 resolved / kind_per_symbol。"""
    tgt = (rec.get("resolved") or "").strip()
    rungs = [ps.get("rung") for ps in (rec.get("kind_per_symbol") or [])]
    for cls in precedence:
        if cls == "target_non_cs":
            if tgt and pathlib.PurePosixPath(tgt).suffix != CS_EXT:
                return cls
        elif cls == "target_unresolved":
            if not tgt:
                return cls
        elif cls == "mixed_rung":
            if len(set(rungs)) >= 2:
                return cls
        elif cls == "pure_code_mention":
            if rungs and set(rungs) == {"code_mention"}:
                return cls
        elif cls == "other_residual":
            return cls
    return "other_residual"


def load(path: pathlib.Path) -> list:
    out = []
    for ln, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"measurement failure: citations.jsonl:{ln} unparsable: {exc}") from exc
    if not out:
        raise RuntimeError("measurement failure: citations.jsonl empty")
    return out


def analyze(recs: list) -> dict:
    live = [r for r in recs]
    weak = [r for r in live if r.get("edge_strength") == "weak"]
    other = [r for r in weak if r.get("edge_kind") == "other"]

    # --- C5 聚合复现 (从逐记录重算四类 kind 计数) ---
    kind_recount = collections.Counter(r.get("edge_kind") for r in live if r.get("edge_kind"))
    # --- C1 分类 + 恰一类 ---
    cls_of = [classify(r) for r in other]
    cls_counts = collections.Counter(cls_of)
    # --- C3 结构可达性 census ---
    def ext_of(r):
        t = (r.get("resolved") or "").strip()
        return pathlib.PurePosixPath(t).suffix if t else "<NONE>"
    strength_ext = collections.defaultdict(collections.Counter)
    for r in live:
        strength_ext[r.get("edge_strength") or "<none>"][ext_of(r)] += 1
    strong = [r for r in live if r.get("edge_strength") == "strong"]
    strong_non_cs = [r for r in strong if ext_of(r) != CS_EXT]
    # --- C4 .py 目标 census ---
    py_weak = [r for r in weak if ext_of(r) == ".py"]
    py_weak_in_other = [r for r in py_weak if r.get("edge_kind") == "other"]
    # --- C7(b) 负控: .cs 目标且含 declared_* rung 的弱边 ---
    declared_weak = [r for r in weak
                     if any((ps.get("rung") or "").startswith("declared_")
                            for ps in (r.get("kind_per_symbol") or []))]
    declared_weak_wrong = [r for r in declared_weak if classify(r) in
                           ("target_non_cs", "target_unresolved", "mixed_rung", "pure_code_mention")]
    # --- C10 口径双栏 ---
    n_scope_out = cls_counts.get("target_non_cs", 0) + cls_counts.get("target_unresolved", 0)
    caliber = {
        "weak_total_as_registered": len(weak),
        "weak_minus_index_scope_out": len(weak) - n_scope_out,
        "index_scope_out_edges": n_scope_out,
        "delta_applied_to_registered_caliber": False,
    }
    # --- C7(c) precedence 置换负控 ---
    perm = ["mixed_rung", "pure_code_mention", "target_non_cs", "target_unresolved", "other_residual"]
    perm_counts = collections.Counter(classify(r, perm) for r in other)

    return {
        "prereg_version": PREREG_VERSION,
        "input_records": len(live),
        "weak_edges": len(weak),
        "other_edges": len(other),
        "other_class_counts": dict(cls_counts),
        "other_class_edges": [
            {"class": classify(r), "symbols": r.get("symbols"),
             "target": r.get("resolved"), "doc": r.get("doc"), "doc_line": r.get("doc_line"),
             "rungs": sorted({ps.get("rung") for ps in (r.get("kind_per_symbol") or [])})}
            for r in other],
        "kind_counts_recomputed": dict(kind_recount),
        "strength_by_target_ext": {k: dict(v) for k, v in strength_ext.items()},
        "strong_edges": len(strong),
        "strong_non_cs": len(strong_non_cs),
        "py_target_weak_edges": len(py_weak),
        "py_target_weak_in_other": len(py_weak_in_other),
        "declared_rung_weak_edges": len(declared_weak),
        "declared_rung_weak_misclassified": len(declared_weak_wrong),
        "caliber": caliber,
        "precedence_permuted_counts": dict(perm_counts),
        "precedence_permutation_changed": perm_counts != cls_counts,
    }


def judge(rep: dict, expected_kinds: dict | None) -> list:
    """返回 [(判据名, ok, 备注)]。"""
    out = []
    c = rep["other_class_counts"]
    out.append(("C1_conservation",
                sum(c.values()) == rep["other_edges"] == 17,
                f"Σclasses={sum(c.values())} other_edges={rep['other_edges']}"))
    out.append(("C2_nontrivial",
                len([1 for v in c.values() if v > 0]) >= 2,
                f"non_zero_classes={len([1 for v in c.values() if v > 0])} dist={c}"))
    out.append(("C3_structural_reachability",
                rep["strong_non_cs"] == 0 and rep["strong_edges"] == 365,
                f"strong={rep['strong_edges']} strong_non_cs={rep['strong_non_cs']}"))
    out.append(("C4_py_target_census",
                rep["py_target_weak_edges"] == rep["py_target_weak_in_other"]
                and rep["py_target_weak_edges"] == c.get("target_non_cs", 0),
                f"py_weak={rep['py_target_weak_edges']} in_other={rep['py_target_weak_in_other']} "
                f"class_target_non_cs={c.get('target_non_cs', 0)}"))
    if expected_kinds is not None:
        out.append(("C5_aggregate_reproduction",
                    rep["kind_counts_recomputed"] == expected_kinds,
                    f"recomputed={rep['kind_counts_recomputed']} registered={expected_kinds}"))
    else:
        out.append(("C5_aggregate_reproduction", False, "no registered aggregate supplied"))
    out.append(("C7b_declared_rung_weak_not_structural",
                rep["declared_rung_weak_misclassified"] == 0,
                f"declared_rung_weak={rep['declared_rung_weak_edges']} "
                f"misclassified={rep['declared_rung_weak_misclassified']}"))
    out.append(("C7c_precedence_effective",
                rep["precedence_permutation_changed"] is True,
                f"default={c} permuted={rep['precedence_permuted_counts']}"))
    out.append(("C8_vacuous_explicit",
                rep["other_edges"] > 0,
                f"other_edges={rep['other_edges']} vacuous={rep['other_edges'] == 0}"))
    out.append(("C10_caliber_not_applied",
                rep["caliber"]["delta_applied_to_registered_caliber"] is False,
                f"registered={rep['caliber']['weak_total_as_registered']} "
                f"minus_scope_out={rep['caliber']['weak_minus_index_scope_out']}"))
    return out


# ---------------------------------------------------------------- selftest
def _rec(strength, kind, target, rungs, syms):
    return {"edge_strength": strength, "edge_kind": kind, "resolved": target,
            "symbols": syms, "doc": "docs/plans/fixture.md", "doc_line": 1,
            "kind_per_symbol": [{"symbol": s, "rung": r} for s, r in zip(syms, rungs)]}


def selftest() -> int:
    fails, lines = [], []

    def chk(name, cond, note=""):
        lines.append(f"  [{'ok' if cond else 'FAIL'}] {name} {note}")
        if not cond:
            fails.append(name)

    # 正控: 每类各一
    fx = [
        _rec("weak", "other", "src/agent/x/Alpha.cs", ["code_mention"], ["AlphaThing"]),
        _rec("weak", "other", "eval/probe/tasks.py", ["code_mention"], ["FAMILIES"]),
        _rec("weak", "other", "src/agent/x/Beta.cs", ["code_mention", "absent"], ["B", "C"]),
        _rec("weak", "other", "src/agent/x/Gamma.cs", ["absent"], ["Gone"]),
        _rec("weak", "other", "", ["code_mention"], ["NoTarget"]),
    ]
    got = [classify(r) for r in fx]
    chk("POS pure_code_mention", got[0] == "pure_code_mention", got[0])
    chk("POS target_non_cs", got[1] == "target_non_cs", got[1])
    chk("POS mixed_rung", got[2] == "mixed_rung", got[2])
    chk("POS other_residual", got[3] == "other_residual", got[3])
    chk("POS target_unresolved", got[4] == "target_unresolved", got[4])
    chk("nonconstant (>=2 distinct classes)", len(set(got)) >= 4, f"{sorted(set(got))}")

    # 负控 (a): .cs 目标不得被判 target_non_cs
    cs_only = [r for r in fx if (r.get("resolved") or "").endswith(".cs")]
    chk("NEG-a no .cs target labelled non_cs",
        all(classify(r) != "target_non_cs" for r in cs_only), f"n={len(cs_only)}")
    # 负控 (b): .cs 目标 + declared_* rung 的弱边 ⇒ 不得落任一结构类
    inj = _rec("weak", "other", "src/agent/x/Delta.cs", ["declared_member"], ["DeltaThing"])
    chk("NEG-b declared rung -> not structural class",
        classify(inj) not in ("target_non_cs", "target_unresolved", "mixed_rung", "pure_code_mention"),
        classify(inj))
    # 负控 (c): precedence 置换必须改变至少一条 (.py + 混面)
    amb = _rec("weak", "other", "eval/probe/run_probe.py", ["code_mention", "absent"], ["A", "B"])
    perm = ["mixed_rung", "pure_code_mention", "target_non_cs", "target_unresolved", "other_residual"]
    chk("NEG-c precedence permutation changes label",
        classify(amb) == "target_non_cs" and classify(amb, perm) == "mixed_rung",
        f"default={classify(amb)} perm={classify(amb, perm)}")
    # 真空控: 空输入 ⇒ 显式 vacuous, 不静默当通过
    rep0 = analyze([_rec("strong", None, "src/agent/x/Alpha.cs", ["declared_type"], ["AlphaThing"])])
    chk("VAC other_edges==0 记为 vacuous 且 C8 判 false",
        rep0["other_edges"] == 0 and judge(rep0, rep0["kind_counts_recomputed"])[7][1] is False,
        f"other_edges={rep0['other_edges']}")
    # 守恒负控: 分类必须穷尽 (恰一类)
    chk("CONS exhaustive single-label", len(got) == len(fx), f"{len(got)}/{len(fx)}")

    print("EXP1-Q11 analyzer selftest")
    print("\n".join(lines))
    print(f"RESULT: {'PASS' if not fails else 'FAIL'} ({len(fails)} failing)")
    return 2 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--citations", default="eval/capability/exp1-q10/citations.jsonl")
    ap.add_argument("--aggregate", default="eval/capability/exp1-q10/attribution_q10.json")
    ap.add_argument("--out", default="eval/capability/exp1-q11/decomposition_q11.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        recs = load(pathlib.Path(a.citations))
        expected = None
        agg_p = pathlib.Path(a.aggregate)
        if agg_p.exists():
            agg = json.loads(agg_p.read_text(encoding="utf-8", errors="replace"))
            expected = agg.get("edge_kind_counts")
    except Exception as exc:                      # 测量/环境失败 (不是断言失败)
        print(f"MEASUREMENT_FAILURE: {exc}")
        return 3
    rep = analyze(recs)
    checks = judge(rep, expected)
    rep["checks"] = [{"name": n, "ok": bool(ok), "note": nt} for n, ok, nt in checks]
    rep["verdict"] = "PASS" if all(ok for _, ok, _ in checks) else "FAIL"
    blob = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rep["output_sha256"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    for n, ok, nt in checks:
        print(f"[{'ok' if ok else 'FAIL'}] {n}: {nt}")
    print(f"other_class_counts = {rep['other_class_counts']}")
    print(f"strength_by_target_ext = {rep['strength_by_target_ext']}")
    print(f"caliber = {rep['caliber']}")
    print(f"VERDICT = {rep['verdict']}  -> {out}")
    return 0 if rep["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
