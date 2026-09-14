#!/usr/bin/env python3
"""exp1-Q3 决策数据探针：近似代码引用图的精度/成本实测（零产品改动，只在 eval/ 内）。

背景：docs/plans/v0.22.0-exp1-local-index-and-code-graph.md §8-Q3 待用户决策
「引用图精度：接受近似图（正则/文本启发，无编译器精度）？」——本探针把该问题
变成数据：在真实 C# 源上跑 §3 提出的启发式，与**人工 ground truth**（§6-A6）对账。

判据（预注册，见 CRITERIA；运行前写死，跑后不得改）：
  E1 召回  recall    = |heuristic ∩ gt| / |gt|            >= 0.80
  E2 精确  precision = |heuristic ∩ gt| / |heuristic|     >= 0.70
  E3 负控1 不存在的符号 => 边数 == 0（fail-closed）
  E4 负控2 短通用词（词面重叠）=> 记录过收量（信息字段，不参与红绿）
  arm2（信息字段，不参与红绿）：先掩码注释/字符串再匹配 —— 观察精确率变化，
  但掩码器自身有已知低估方向偏差（不处理字符字面量、插值表达式内部），只作观察。

三态退出码（与 skill `unattended-job-reliability` §3 一致）：
  0 = 判据全过 / 2 = 断言失败 / 3 = 测量或环境失败（范围缺失等）

范围（scope）：仓库内 src/**/*.cs，排除 bin/ obj/（构建产物不是源）。

诚实边界（写入 result.json）：
  - fixture 下 **召回结构性恒为 1.0**：GT 边集合 ⊂ 词面出现行集合，而启发式把
    「任何词面出现行」都当边 ⇒ 本 fixture 真正有判别力的是**精确率**，不是召回。
  - GT 由本 agent 人工判读枚举输出得到（非第三方独立标注）。
  - 召回的真实风险（间接引用：接口/DI 字符串/反射）不在本 fixture 覆盖范围内。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

CRITERIA = {
    "recall_min": 0.80,
    "precision_min": 0.70,
    "negative_control_missing_symbol_edges": 0,
    "note": "预注册于本轮运行前；未通过时如实记录，不改阈值",
}

SKIP_DIRS = {"bin", "obj", ".git", "node_modules"}


def in_scope_files(root: Path, suffix=".cs"):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(suffix):
                yield Path(dirpath) / fn


def token_re(sym: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(sym) + r"(?![A-Za-z0-9_])")


def load_scope(scope: Path):
    """读入范围内所有文件（一次），返回 [(relpath, lines)]；errors=replace 防非 UTF-8 崩批。"""
    out = []
    for p in in_scope_files(scope):
        try:
            text = p.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        out.append((str(p.relative_to(REPO)), text.splitlines()))
    return out


def mask_noncode(text: str) -> str:
    """把注释与字符串字面量替换为等长空白（保留 \\n ⇒ 行号对齐）。仅作观察臂。"""
    out = []
    i, n, state, rawq = 0, len(text), "normal", 0
    while i < n:
        c = text[i]
        if state == "normal":
            if c == "/" and i + 1 < n and text[i + 1] == "/":
                state = "line"; out.append("  "); i += 2; continue
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                state = "block"; out.append("  "); i += 2; continue
            if text.startswith('"""', i):
                q = 0
                while i + q < n and text[i + q] == '"':
                    q += 1
                state, rawq = "raw", q
                out.append(" " * q); i += q; continue
            if c == "@" and i + 1 < n and text[i + 1] == '"':
                state = "verbatim"; out.append("  "); i += 2; continue
            if c == '"':
                state = "string"; out.append(" "); i += 1; continue
            if c == "'":
                state = "char"; out.append(" "); i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                out.append("\n"); state = "normal"; i += 1; continue
            out.append(" "); i += 1; continue
        if state == "block":
            if text.startswith("*/", i):
                out.append("  "); state = "normal"; i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        if state == "string":
            if c == "\\" and i + 1 < n:
                out.append("  "); i += 2; continue
            if c == '"':
                out.append(" "); state = "normal"; i += 1; continue
            if c == "\n":
                # C# 非 verbatim 字符串不能跨行：行内未闭合 ⇒ 必须复位，否则吞噬后续真代码
                out.append("\n"); state = "normal"; i += 1; continue
            out.append(" "); i += 1; continue
        if state == "char":
            if c == "\\" and i + 1 < n:
                out.append("  "); i += 2; continue
            if c == "'":
                out.append(" "); state = "normal"; i += 1; continue
            if c == "\n":
                out.append("\n"); state = "normal"; i += 1; continue
            out.append(" "); i += 1; continue
        if state == "verbatim":
            if text.startswith('""', i):
                out.append("  "); i += 2; continue
            if c == '"':
                out.append(" "); state = "normal"; i += 1; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        # state == "raw"
        if text.startswith('"' * rawq, i):
            out.append(" " * rawq); state = "normal"; i += rawq; continue
        out.append("\n" if c == "\n" else " "); i += 1; continue
    return "".join(out)


DEF_RE_TMPL = r"\b(?:class|record|struct|interface|enum|delegate)\s+" + r"{sym}\b"


def classify(sym: str, corpus):
    """启发式（§3 方案 C）：词面出现即边；命中声明式者记 def。"""
    tre = token_re(sym)
    defre = re.compile(r"\b(?:class|record|struct|interface|enum|delegate)\s+" + re.escape(sym) + r"\b")
    defs, refs = [], []
    for rel, lines in corpus:
        for i, line in enumerate(lines, 1):
            if tre.search(line):
                (defs if defre.search(line) else refs).append((rel, i))
    return defs, refs


def enumerate_symbol(sym: str, corpus):
    tre = token_re(sym)
    rows = []
    for rel, lines in corpus:
        for i, line in enumerate(lines, 1):
            if tre.search(line):
                rows.append((rel, i))
    return rows


def score(edges, want):
    got = set(edges)
    hit = got & want
    return {"got_n": len(got), "gt_n": len(want), "tp": len(hit),
            "fp": len(got - want), "fn": len(want - got),
            "fp_rows": sorted(f"{f}:{l}" for f, l in (got - want))[:12],
            "fn_rows": sorted(f"{f}:{l}" for f, l in (want - got))[:12]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="src")
    ap.add_argument("--enumerate", nargs="*", default=None)
    ap.add_argument("--gt", default=str(OUT / "groundtruth.json"))
    ap.add_argument("--result", default=str(OUT / "result.json"))
    args = ap.parse_args()

    scope = REPO / args.scope
    if not scope.is_dir():
        print(json.dumps({"error": "scope_missing", "scope": str(scope)}))
        return 3

    t0 = time.perf_counter()
    corpus = load_scope(scope)
    scan_ms = (time.perf_counter() - t0) * 1000.0
    if not corpus:
        print(json.dumps({"error": "scope_empty", "scope": str(scope)}))
        return 3

    if args.enumerate is not None:
        for sym in args.enumerate:
            rows = enumerate_symbol(sym, corpus)
            print(f"### {sym}: {len(rows)} occurrence(s)")
            lines_by_rel = {rel: lines for rel, lines in corpus}
            for rel, i in rows:
                text = lines_by_rel[rel][i - 1].strip()
                print(f"{rel}:{i}: {text[:200]}")
        print(json.dumps({"scope": str(scope), "files": len(corpus), "scan_ms": round(scan_ms, 1)}))
        return 0

    gt_doc = json.loads(Path(args.gt).read_text(encoding="utf-8"))
    syms = gt_doc["symbols"]
    criterion_symbols = gt_doc.get("criterion_symbols") or list(syms.keys())
    holdout = gt_doc.get("holdout_symbols") or []
    negative = gt_doc.get("negative_controls", {})

    def expected(sym):
        return {(f, l) for f, l, cls in syms[sym]["rows"] if cls == "edge"}

    def cls_of(sym, key):
        for f, l, cls in syms[sym]["rows"]:
            if (f, l) == key:
                return cls
        return "not_in_gt"

    # arm1 = 现行启发式（原始文本）
    per_symbol, tp, fp, fn = {}, 0, 0, 0
    fp_by_class: dict[str, int] = {}
    for sym in criterion_symbols:
        defs, refs = classify(sym, corpus)
        st = score([(f, l) for f, l in defs] + [(f, l) for f, l in refs], expected(sym))
        for row in st["fp_rows"]:
            f, l = row.rsplit(":", 1)
            k = cls_of(sym, (f, int(l)))
            fp_by_class[k] = fp_by_class.get(k, 0) + 1
        per_symbol[sym] = st
        tp += st["tp"]; fp += st["fp"]; fn += st["fn"]

    recall = tp / (tp + fn) if (tp + fn) else None
    precision = tp / (tp + fp) if (tp + fp) else None

    # arm2 = 先掩码非代码再匹配（观察臂）
    t1 = time.perf_counter()
    corpus_masked = [(rel, mask_noncode("\n".join(lines)).split("\n")) for rel, lines in corpus]
    mask_ms = (time.perf_counter() - t1) * 1000.0
    tp2 = fp2 = fn2 = 0
    per_symbol2 = {}
    for sym in criterion_symbols:
        defs, refs = classify(sym, corpus_masked)
        st = score([(f, l) for f, l in defs] + [(f, l) for f, l in refs], expected(sym))
        per_symbol2[sym] = st
        tp2 += st["tp"]; fp2 += st["fp"]; fn2 += st["fn"]
    recall2 = tp2 / (tp2 + fn2) if (tp2 + fn2) else None
    precision2 = tp2 / (tp2 + fp2) if (tp2 + fp2) else None

    # 负控 1：不存在的符号 ⇒ 零边（fail-closed）
    nc_missing = {}
    for sym in negative.get("missing_symbols", []):
        defs, refs = classify(sym, corpus)
        nc_missing[sym] = len(defs) + len(refs)
    nc1_ok = bool(nc_missing) and all(v == CRITERIA["negative_control_missing_symbol_edges"]
                                     for v in nc_missing.values())

    # 负控 2：短通用词 —— 词边界匹配 vs 逐字（substring）匹配的过收量
    nc_substr = {}
    for sym in negative.get("overmatching_symbols", []):
        exact = len(enumerate_symbol(sym, corpus))
        substring = sum(1 for _, lines in corpus for line in lines if sym in line)
        nc_substr[sym] = {"exact_token_rows": exact, "substring_rows": substring,
                          "overcollect": substring - exact,
                          "ratio": round(substring / exact, 3) if exact else None}

    # 留出符号（不参与红绿，仅泛化观察）
    holdout_read = {}
    for sym in holdout:
        if sym in syms:
            defs, refs = classify(sym, corpus)
            holdout_read[sym] = score([(f, l) for f, l in defs] + [(f, l) for f, l in refs], expected(sym))

    if recall is None or precision is None:
        verdict = "ABSTAIN"
    else:
        verdict = "PASS" if (recall >= CRITERIA["recall_min"]
                             and precision >= CRITERIA["precision_min"] and nc1_ok) else "FAIL"

    out = {
        "step": "EXP1-Q3",
        "criteria": CRITERIA,
        "scope": {"path": args.scope, "files": len(corpus), "scan_ms": round(scan_ms, 1),
                  "mask_ms": round(mask_ms, 1)},
        "criterion_symbols": criterion_symbols,
        "arm1_raw_heuristic": {
            "readings": {"recall": None if recall is None else round(recall, 4),
                         "precision": None if precision is None else round(precision, 4),
                         "tp": tp, "fp": fp, "fn": fn},
            "per_symbol": per_symbol,
            "fp_by_gt_class": fp_by_class,
        },
        "arm2_mask_noncode": {
            "readings": {"recall": None if recall2 is None else round(recall2, 4),
                         "precision": None if precision2 is None else round(precision2, 4),
                         "tp": tp2, "fp": fp2, "fn": fn2},
            "per_symbol": per_symbol2,
            "note": "观察臂（不参与红绿）；掩码器不处理字符字面量与插值表达式内部 ⇒ 低估方向偏差",
        },
        "negative_control_missing": nc_missing,
        "negative_control_missing_ok": nc1_ok,
        "negative_control_overmatching": nc_substr,
        "holdout_observation": holdout_read,
        "verdict": verdict,
        "honest_boundaries": [
            "本 fixture 召回结构性恒为 1.0（GT 边 ⊂ 词面出现行），有判别力的是精确率",
            "GT 由本 agent 人工判读（自建 fixture，非第三方独立标注）",
            "间接引用（接口/DI 字符串/反射）不在本 fixture 覆盖范围，召回风险未被测量",
        ],
        "gt_source": gt_doc.get("provenance", ""),
    }
    Path(args.result).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("step", "arm1_raw_heuristic", "arm2_mask_noncode",
                                          "negative_control_missing",
                                          "negative_control_overmatching", "verdict")},
                     ensure_ascii=False, indent=2))
    if verdict == "PASS":
        return 0
    return 2 if verdict == "FAIL" else 3


if __name__ == "__main__":
    sys.exit(main())
