#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q10 弱边细分全量清单 (人工可审计): 每一条弱边一个 kind + 逐符号证据 + 被引文件上下文行。

输入: attribution_q10.json (由 probe_v260.py --out 产出, 内含 citations 全量记录)。
输出: weak_kind_table.json / weak_kind_table.md (与 Q9 的 weak_edge_table.* 同形态)。
上下文行口径与 Q9 检查器一致: 「出现面」(in_code_face) 用 strip_noncode 后的代码面文本判定 —— 
在代码面出现 = code_identifier, 否则看是否落在引号区 = string_literal, 再否则 = comment。
"""
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
ATTR = HERE / "attribution_q10.json"


def load_probe():
    spec = importlib.util.spec_from_file_location("probe_arm", HERE / ("probe_v270.py" if (HERE / "probe_v270.py").is_file() else "probe_v260.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = load_probe()


def occ_source(text: str, code_text: str, sym: str, line: str) -> str:
    pat = r'\b' + re.escape(sym) + r'\b'
    if re.search(pat, code_text):
        return "code_identifier"
    m = re.search(pat, line)
    if m:
        before = line[:m.start()]
        if before.count('"') % 2 == 1:
            return "string_literal"
    return "comment"


def main():
    if not ATTR.is_file():
        print(json.dumps({"stage": "precheck", "error": "attribution_q10.json missing",
                          "hint": "先跑 probe_v260.py --out attribution_q10.json", "exit_code": 3}))
        return 3
    jsonl = HERE / "citations.jsonl"
    if not jsonl.is_file():
        print(json.dumps({"stage": "precheck", "error": "citations.jsonl missing",
                          "hint": "citations.jsonl 由 probe_v260.py 与被引文件同目录落盘", "exit_code": 3}))
        return 3
    res = json.loads(ATTR.read_text(encoding="utf-8"))
    cites = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    repo = P.Repo(REPO)
    weak = [c for c in cites
            if c.get("edge_strength") == "weak" and not c.get("in_code_fence") and c.get("kind") == "code"]
    rows = []
    for c in weak:
        rel = c.get("resolved")
        text, _sha = (repo.read(rel) if rel else (None, None))
        code_text = repo.codeface(rel) if rel else None
        ctx = []
        if text is not None and c.get("line_start"):
            lines = text.splitlines()
            for ln in range(max(1, c["line_start"]), min(len(lines), c["line_end"] or c["line_start"]) + 1):
                line = lines[ln - 1]
                hit = [s for s in (c.get("symbols") or []) if re.search(r'\b' + re.escape(s) + r'\b', line)]
                ctx.append({"line": ln,
                            "in_code_face": bool(code_text and re.search(
                                r'\b' + re.escape(hit[0]) + r'\b', code_text.splitlines()[ln - 1]) if hit else False),
                            "occ_source": occ_source(text, code_text or "", hit[0], line) if hit else "n/a",
                            "text": line.strip()[:160]})
        rows.append({
            "doc": c["doc"], "doc_line": c["doc_line"], "raw": (c.get("raw") or "")[:180],
            "path": c["path"], "resolved": rel, "verdict": c["verdict"],
            "line_start": c.get("line_start"), "line_end": c.get("line_end"),
            "symbols": c.get("symbols"), "rungs": (c.get("kind_per_symbol") and
                                                   {p["symbol"]: p["rung"] for p in c["kind_per_symbol"]}),
            "edge_kind": c.get("edge_kind"), "kind_reason": c.get("kind_reason"),
            "kind_per_symbol": c.get("kind_per_symbol"),
            "input_sha": c.get("input_sha"),
            "n_context_lines": len(ctx), "contexts": ctx,
        })
    kc = Counter(r["edge_kind"] for r in rows)
    summary = {
        "unit": "引用级边 (edge); 符号级计数另见 weak_symbol_kind_counts",
        "n_weak_edges": len(rows),
        "edge_kind_counts": dict(kc),
        "kind_precedence": "cross_file > named_fact > comment_only > other",
        "n_edges_with_context": sum(1 for r in rows if r["n_context_lines"] >= 1),
        "n_edges_unresolved": sum(1 for r in rows if not r["resolved"]),
        "symbol_kind_counts": dict(Counter(p["symbol_kind"] for r in rows
                                          for p in (r["kind_per_symbol"] or []))),
        "declared_elsewhere_visible": sum(1 for r in rows for p in (r["kind_per_symbol"] or [])
                                          if p["declared_elsewhere"] >= 1),
        "probe_version": res.get("probe_version"),
        "instrument_sha256": hashlib.sha256((HERE / "probe_v260.py").read_bytes()).hexdigest(),
    }
    checks = {
        "all_edges_have_context": all(r["n_context_lines"] >= 1 for r in rows),
        "conservation": sum(kc.values()) == len(rows) == res.get("n_weak_edges"),
        "kinds_nontrivial": len(kc) >= 2,
        "all_kinds_in_preregistered_set": set(kc) <= set(P.WEAK_KINDS),
        "every_edge_classified": all(r["edge_kind"] in P.WEAK_KINDS for r in rows),
    }
    out = {"summary": summary, "checks": checks, "all_checks_pass": all(checks.values()), "edges": rows}
    (HERE / "weak_kind_table.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# EXP1-Q10 弱边细分全量清单 (v{res.get('probe_version')})", ""]
    md.append(f"- 弱边数: {len(rows)} / kind 分布: {dict(kc)}")
    md.append(f"- 符号级分布: {summary['symbol_kind_counts']}")
    md.append(f"- 检查: {checks}")
    md.append("")
    for kind in P.WEAK_KINDS:
        sub = [r for r in rows if r["edge_kind"] == kind]
        md.append(f"## {kind} ({len(sub)})")
        for r in sub:
            md.append(f"- `{r['doc_line']}` {r['path']}:{r['line_start']}-{r['line_end']} "
                      f"符号={r['symbols']} 面={r['rungs']}")
            md.append(f"  - 依据: {r['kind_reason']}")
            for p in (r["kind_per_symbol"] or []):
                md.append(f"    - `{p['symbol']}` 形态={p['shape']} 面={p['rung']} "
                          f"他处声明={p['declared_elsewhere']} {p['declared_elsewhere_files']}")
            for cx in r["contexts"]:
                md.append(f"    - L{cx['line']} [{cx['occ_source']}] {cx['text']}")
        md.append("")
    (HERE / "weak_kind_table.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({"n_weak_edges": len(rows), "edge_kind_counts": dict(kc),
                      "symbol_kind_counts": summary["symbol_kind_counts"],
                      "checks": checks, "all_checks_pass": out["all_checks_pass"],
                      "exit_code": 0 if out["all_checks_pass"] else 2}, ensure_ascii=False, indent=2))
    return 0 if out["all_checks_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
