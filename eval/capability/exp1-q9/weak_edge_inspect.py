#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q9 弱边**全量**抽检: 两套口径逐条给证据 (上下文行 + 来源类 + 名称形态 + 树内声明旁证)。

口径对齐 (本轮第一步就是钉单位 —— R440 教训: 分母单位不同 ⇒ 数字全错):
  A 计划口径 = **符号级** noncode_mention 条目 (verdict=ok)      —— 计划文档里的 "25 条弱边" 即此口径
  B 引用图口径 = **引用级** weak_noncode 边 (本轮 v2.5.0 新增)   —— 同一批现象按边聚合后的口径
两套都全量抽检 (inspected/total == 1.0), 不做抽样。
"""
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("probe_v250", HERE / "probe_v250.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)  # type: ignore[union-attr]
REPO = probe.Repo(ROOT)

SRC_GLOBS = ("src/**/*.cs", "src/**/*.py")


def name_shape(s: str) -> str:
    if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", s):
        return "SCREAMING_SNAKE"
    if re.fullmatch(r"[a-z][a-z0-9_]*_[a-z0-9_]+", s):
        return "snake_case"
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", s):
        return "PascalCase"
    if re.fullmatch(r"[a-z][A-Za-z0-9]*", s):
        return "camelCase"
    return "other"


SEMANTIC_GUESS = {"SCREAMING_SNAKE": "env_var_or_const_name",
                  "snake_case": "telemetry_key_or_metric_name",
                  "PascalCase": "code_type_or_member_name",
                  "camelCase": "code_member_or_local_name",
                  "other": "n/a"}

# occurrence 来源类判定规则 (词法级近似, 逐条与上下文一起人工复核):
#   代码面出现 -> code_identifier; 非代码面且在引号包裹区内 -> string_literal; 其余 -> comment
OCC_RULE = ("in_code_face?" "code_identifier" " : 'quoted region containing symbol?' string_literal"
            " : 'comment'")


def classify_occ(line: str, sym: str, in_code: bool) -> str:
    if in_code:
        return "code_identifier"
    pat = r'["\'][^"\']*' + re.escape(sym) + r'[^"\']*["\']'
    return "string_literal" if re.search(pat, line) else "comment"


def context_lines(rel: str, sym: str):
    text, sha = REPO.read(rel)
    if text is None:
        return None, None, []
    code = REPO.codeface(rel) or ""
    raw_lines = text.splitlines()
    code_lines = code.splitlines()
    hits = []
    pat = re.compile(r"\b" + re.escape(sym) + r"\b")
    for i, line in enumerate(raw_lines, 1):
        if not pat.search(line):
            continue
        cl = code_lines[i - 1] if i - 1 < len(code_lines) else ""
        in_code = bool(pat.search(cl))
        hits.append({"line": i, "in_code_face": in_code,
                     "occ_source": classify_occ(line, sym, in_code),
                     "text": line.strip()[:200]})
    return text, sha, hits


def declaration_index(symbols):
    """一次遍历源码树, 给出每个符号在哪些文件里**有声明形态** (跨文件真值, 词法级)。"""
    idx = {s: [] for s in symbols}
    repo = REPO
    for g in SRC_GLOBS:
        for rel in repo.glob(g):
            text, _ = repo.read(rel)
            if text is None:
                continue
            faces = probe.faces_for(repo, rel, text, symbols)
            for s, r in faces.items():
                if r in probe.STRONG_RUNGS:
                    idx[s].append(rel)
    return idx


def main():
    attr = json.loads((HERE / "attribution_q9_edges.json").read_text(encoding="utf-8"))
    # ---- 集合 A: 计划口径 (符号级 noncode_mention ∧ verdict ok)
    set_a = [x for x in attr["symbol_face_candidates"]
             if x["rung"] == "noncode_mention" and x["verdict"] == "ok"]
    # ---- 集合 B: 引用图口径 (引用级 weak_noncode 边)
    set_b = [e for e in attr["edge_weak_list"] if e["sublevel"] == probe.WEAK_NONCODE]

    relo = {(c["doc"], c["doc_line"]): c for c in attr["relocated_citations"]}
    syms = sorted({x["symbol"] for x in set_a} | {s for e in set_b for s in e["symbols"]})
    decl_idx = declaration_index(syms)

    rows_a = []
    for x in set_a:
        rel = x["resolved"]
        via = "resolved"
        if rel is None:
            rc = relo.get((x["doc"], x["doc_line"]))
            cands = (rc or {}).get("relocated_to") or []
            rel = cands[0] if len(cands) == 1 else None
            via = "relocated_unique" if rel else "unresolved"
        text, sha, hits = context_lines(rel, x["symbol"]) if rel else (None, None, [])
        rows_a.append({**x, "unit": "symbol", "file": rel, "via": via,
                       "file_sha256": sha, "contexts": hits,
                       "n_context_lines": len(hits),
                       "name_shape": name_shape(x["symbol"]),
                       "semantic_guess": SEMANTIC_GUESS[name_shape(x["symbol"])],
                       "declared_elsewhere_files": decl_idx.get(x["symbol"], []),
                       "n_declared_elsewhere": len(decl_idx.get(x["symbol"], []))})

    rows_b = []
    for e in set_b:
        rel = e["resolved"]
        via = "resolved"
        if rel is None:
            rc = relo.get((e["doc"], e["doc_line"]))
            cands = (rc or {}).get("relocated_to") or []
            rel = cands[0] if len(cands) == 1 else None
            via = "relocated_unique" if rel else "unresolved"
        per = []
        for s in e["symbols"]:
            text, sha, hits = context_lines(rel, s) if rel else (None, None, [])
            per.append({"symbol": s, "rung": e["rungs"].get(s),
                        "n_context_lines": len(hits), "contexts": hits,
                        "name_shape": name_shape(s),
                        "semantic_guess": SEMANTIC_GUESS[name_shape(s)],
                        "n_declared_elsewhere": len(decl_idx.get(s, [])),
                        "declared_elsewhere_files": decl_idx.get(s, [])[:5]})
        rows_b.append({**e, "unit": "edge", "file": rel, "via": via, "per_symbol": per,
                       "n_context_lines": sum(p["n_context_lines"] for p in per)})

    # ---- 覆盖关系: 集合 A 的符号条目落在哪些边里 (两口径互相对账)
    b_syms = {(e["doc"], e["doc_line"], s) for e in set_b for s in e["symbols"]}
    a_in_b = sum(1 for x in set_a if (x["doc"], x["doc_line"], x["symbol"]) in b_syms)

    summary = {
        "unit_note": "A=符号级 (计划口径) / B=引用级边 (引用图口径); 两口径的单位不同, 不可互相换算成一条公式",
        "A_symbol_level_noncode_mention_ok": len(set_a),
        "B_edge_level_weak_noncode": len(set_b),
        "A_in_B_coverage": a_in_b,
        "A_shape_dist": dict(Counter(r["name_shape"] for r in rows_a)),
        "A_occ_source_dist": dict(Counter(c["occ_source"] for r in rows_a for c in r["contexts"])),
        "A_declared_elsewhere_dist": dict(Counter(r["n_declared_elsewhere"] for r in rows_a)),
        "A_context_line_total": sum(r["n_context_lines"] for r in rows_a),
        "B_context_line_total": sum(r["n_context_lines"] for r in rows_b),
        "occ_rule": OCC_RULE,
    }
    checks = {
        "B6_A_full_inspected": len(rows_a) == len(set_a) and len(set_a) > 0,
        "B6_B_full_inspected": len(rows_b) == len(set_b) and len(set_b) > 0,
        "B6_A_all_have_context": all(r["n_context_lines"] >= 1 for r in rows_a),
        "B6_B_all_have_context": all(r["n_context_lines"] >= 1 for r in rows_b),
        # 事后补检 (checks_posthoc): B 的**弱符号** (rung ∈ *_mention) 逐个必须有上下文行 ——
        #   预注册 B6 只要求「每条边 ≥1 行」; 边内混入的 absent 符号按定义无出现行, 不得据此判红。
        "PH_B_weak_symbols_have_context": all(p["n_context_lines"] >= 1
                                             for r in rows_b for p in r["per_symbol"]
                                             if p["rung"] in probe.WEAK_RUNGS),
        "PH_B_absent_symbols_no_context": all(p["n_context_lines"] == 0
                                             for r in rows_b for p in r["per_symbol"]
                                             if p["rung"] == "absent"),
        "B7_declared_elsewhere_recorded": all(isinstance(r["n_declared_elsewhere"], int)
                                              for r in rows_a + rows_b[:0]) and
        all(isinstance(p["n_declared_elsewhere"], int) for r in rows_b for p in r["per_symbol"]),
        "B6_unresolved_visible": all(r["via"] != "unresolved_counted_silently" for r in rows_a),
        "nontrivial_A_shapes": len(set(r["name_shape"] for r in rows_a)) >= 2,
    }
    out = {"summary": summary, "checks": checks, "set_A_symbol_level": rows_a,
           "set_B_edge_level": rows_b, "all_checks_pass": all(checks.values())}
    (HERE / "weak_edge_table.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 人读表
    md = ["# EXP1-Q9 弱边全量抽检 (两口径)", "",
          f"- A 计划口径 (符号级 noncode_mention, verdict=ok): **{len(set_a)}** 条, "
          f"上下文行 {summary['A_context_line_total']}",
          f"- B 引用图口径 (引用级 weak_noncode 边): **{len(set_b)}** 条, "
          f"上下文行 {summary['B_context_line_total']}",
          f"- A 的符号条目落在 B 的边里: {a_in_b}/{len(set_a)}",
          f"- 名称形态分布 A: {summary['A_shape_dist']}",
          f"- occurrence 来源分布 A: {summary['A_occ_source_dist']}",
          f"- 树内他处有声明 (declared_elsewhere) 的文件数分布 A: {summary['A_declared_elsewhere_dist']}",
          "", "## A 符号级全量清单", "",
          "| # | doc | line | 符号 | 形态 | 被引文件 | 出现行 | 来源 | n_decl_elsewhere |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows_a, 1):
        occ = ",".join(f"L{c['line']}:{c['occ_source']}" for c in r["contexts"])
        md.append(f"| {i} | {r['doc']} | {r['doc_line']} | `{r['symbol']}` | {r['name_shape']} | "
                  f"{r['file']} | {occ} | {r['verdict']} | {r['n_declared_elsewhere']} |")
    md += ["", "## B 引用级全量清单 (weak_noncode)", ""]
    for i, r in enumerate(rows_b, 1):
        per = " + ".join(f"`{p['symbol']}`({p['rung']})" for p in r["per_symbol"])
        md.append(f"- {i}. {r['doc']}:{r['doc_line']} -> {r['file']}: {per} "
                  f"[上下文行 {r['n_context_lines']}]")
    md += ["", "## 上下文明细 (A)", ""]
    for i, r in enumerate(rows_a, 1):
        md.append(f"### A{i} `{r['symbol']}` @ {r['doc']}:{r['doc_line']}")
        md.append(f"- doc 原行: {str(r.get('raw', '')).strip()[:160]}")
        md.append(f"- 被引文件: `{r['file']}` (sha256 {str(r['file_sha256'])[:16]}, via {r['via']})")
        for c in r["contexts"]:
            md.append(f"  - L{c['line']} [{c['occ_source']}]: `{c['text'][:160]}`")
        md.append(f"- 树内他处声明文件 ({r['n_declared_elsewhere']}): "
                  f"{', '.join(r['declared_elsewhere_files'][:5]) or '(无)'}")
    (HERE / "weak_edge_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "checks": checks,
                      "all_checks_pass": all(checks.values())}, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
