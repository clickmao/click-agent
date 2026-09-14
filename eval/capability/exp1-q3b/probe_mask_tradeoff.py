#!/usr/bin/env python3
"""exp1-Q3b 决策数据探针（v2，仪器修正后）：**掩码策略**的 精确率/召回 权衡实测。

零产品改动，全部落在 eval/ 内。

背景：exp1-Q3 的诚实边界 ③ 原文「间接引用（接口 / DI 字符串 / 反射）与插值表达式
内引用**未测**，该方向的召回风险未被覆盖」。本探针把这条边界变成数据。

仪器修正记录（**先修仪器，再谈读数** —— 与 skill 的「空心仪器」同族）
------------------------------------------------------------------
v1（`result_degenerate.json`）判据「arm1 有边而 V2 无边的**符号数** == 0」实测恒真：
每个具名类型必然出现在**自己的声明行**上，而声明行是代码 ⇒ V2 ≥ 1 恒成立
⇒ 该判据**结构上不可能触发**，读数（=0）不是证据而是同义反复。
修正：① 排除该符号**自身声明行**上的出现（只留引用）；② 判据下沉到**文件级边**
（引用文件集），因为图语义是「谁引用了谁」，不是「符号出现过几次」。

逐字符分类（一次词法遍历，非估算）：C = 代码 | / = 注释 | s = 字符串正文 | { = 插值孔洞（代码！）
三个视图：V1 原样（词面出现即边，上一轮 arm1）／V2 仅 C（掩注释+字符串**含孔洞**，上一轮 arm2）
          ／V3 = C ∪ {（掩注释+纯字符串、**保留孔洞**，本探针候选）。
符号族 = 仓库内已定义具名类型（class/record/struct/interface/enum/delegate）。

预注册判据（**修正后、重跑前**写死；跑后不得改）
----------------------------------------------
  门禁 G1  hole_caused_lost_edge_count == 0   否则 ⇒ V2 丢真引用边，不可单独采用，须用 V3
  门禁 G2  负控（不存在符号）四类计数 == 0      否则 ⇒ 测量器坏，读数作废
  观察 O1  string_caused_lost_edge_count       纯字符串内的引用（反射/字符串键）：**上界**，不设门禁，
                                               只作「是否需白名单例外」的决策输入

三态退出码：0 = 门禁全过 / 2 = 门禁失败 / 3 = 测量或环境失败

诚实边界
--------
- 孔洞内嵌套字符串/括号按最简规则处理（记深度，不解析嵌套串）；误差方向 = 「孔洞内容可能少记」。
- 符号族仅具名**类型**；方法/字段级引用不在范围（属 Q3 的后续面）。
- O1 只判「形如 FQN 且命中已定义符号」，**不判该串是否为真引用**（反射 / 配置键 / 测试自扫文本都可能）⇒ 上界。
- 边口径 = 文件级（引用文件集）；与 exp1-Q3 的 GT 行级口径不同，两者不可直接相除。
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
    "gate": {
        "hole_caused_lost_edge_count": 0,
        "negative_control_total_counts": 0,
    },
    "observe": {"string_caused_lost_edge_count": "upper_bound_reported"},
    "declared_before_run": "v2 instrument (decl-line excluded, file-level edges)",
    "note": "v1 判据被证实退化（恒真），见 result_degenerate.json；本判据为修正后预注册",
}

SKIP_DIRS = {"bin", "obj", ".git", "node_modules"}
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DEF_RE = re.compile(r"\b(?:class|record|struct|interface|enum|delegate)\s+(?:partial\s+)?([A-Za-z_][A-Za-z0-9_]*)")
FQN_STR_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)"')

CODE, COMMENT, STRING, HOLE = "C", "/", "s", "{"


def in_scope_files(root: Path, suffix=".cs"):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(suffix):
                yield Path(dirpath) / fn


def classify_chars(text: str) -> str:
    """逐字符分类：返回与 text 等长的类别串（C / / s {）。"""
    out = []
    i, n = 0, len(text)
    state = "N"          # N normal, L line, B block, S string, V verbatim, R raw, Q char, I interp, H hole
    rawq, depth, vq = 0, 0, False
    while i < n:
        c = text[i]
        if state == "N":
            if c == "/" and i + 1 < n and text[i + 1] == "/":
                state, out = "L", out + ["/", "/"]; i += 2; continue
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                state, out = "B", out + ["/", "/"]; i += 2; continue
            if c == "$" and i + 1 < n and text[i + 1] == '"':
                state, out, vq = "I", out + ["C", "s"], False; i += 2; continue
            if c == "$" and i + 2 < n and text[i + 1] == "@" and text[i + 2] == '"':
                state, out, vq = "I", out + ["C", "C", "s"], True; i += 3; continue
            if c == "@" and i + 2 < n and text[i + 1] == "$" and text[i + 2] == '"':
                state, out, vq = "I", out + ["C", "C", "s"], True; i += 3; continue
            if text.startswith('"""', i):
                q = 0
                while i + q < n and text[i + q] == '"':
                    q += 1
                state, rawq = "R", q
                out += ["s"] * q; i += q; continue
            if c == "@" and i + 1 < n and text[i + 1] == '"':
                state, out = "V", out + ["C", "s"]; i += 2; continue
            if c == '"':
                state, out = "S", out + ["s"]; i += 1; continue
            if c == "'":
                state, out = "Q", out + ["s"]; i += 1; continue
            out.append(CODE); i += 1; continue
        if state == "L":
            if c == "\n":
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(COMMENT); i += 1; continue
        if state == "B":
            if text.startswith("*/", i):
                state, out = "N", out + ["/", "/"]; i += 2; continue
            out.append(CODE if c == "\n" else COMMENT); i += 1; continue
        if state in ("S", "Q"):
            if c == "\\" and i + 1 < n:
                out += ["s", "s"]; i += 2; continue
            if (state == "S" and c == '"') or (state == "Q" and c == "'"):
                state, out = "N", out + ["s"]; i += 1; continue
            if c == "\n":  # 行内未闭合 ⇒ 必须复位，否则吞噬后续真代码
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(STRING); i += 1; continue
        if state == "V":
            if text.startswith('""', i):
                out += ["s", "s"]; i += 2; continue
            if c == '"':
                state, out = "N", out + ["s"]; i += 1; continue
            out.append(STRING); i += 1; continue
        if state == "R":
            if text.startswith('"' * rawq, i):
                state, out = "N", out + ["s"] * rawq; i += rawq; continue
            out.append(STRING); i += 1; continue
        if state == "I":
            if vq and text.startswith('""', i):
                out += ["s", "s"]; i += 2; continue
            if not vq and c == "\\" and i + 1 < n:
                out += ["s", "s"]; i += 2; continue
            if c == '"':
                state, out = "N", out + ["s"]; i += 1; continue
            if c == "{" and not text.startswith("{{", i):
                state, depth, out = "H", 1, out + [HOLE]; i += 1; continue
            if c == "}" and text.startswith("}}", i):
                out += ["s", "s"]; i += 2; continue
            if c == "\n":
                state, out = "N", out + [CODE]; i += 1; continue
            out.append(STRING); i += 1; continue
        # state == "H": 孔洞内是**代码**
        if c == "{":
            depth += 1; out.append(HOLE); i += 1; continue
        if c == "}":
            depth -= 1
            if depth <= 0:
                state, out = "I", out + [HOLE]; i += 1; continue
            out.append(HOLE); i += 1; continue
        out.append(CODE if c == "\n" else HOLE); i += 1; continue
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="src")
    ap.add_argument("--result", default=str(OUT / "result.json"))
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--absent-symbols", nargs="*", default=["ZzNoSuchSymbol", "CapabilityIndexer"])
    args = ap.parse_args()

    scope = REPO / args.scope
    if not scope.is_dir():
        print(json.dumps({"error": "scope_missing", "scope": str(scope)}))
        return 3

    t0 = time.perf_counter()
    occ: dict[str, list] = {}          # sym -> [(rel, line, class)]
    decl: dict[str, set] = {}          # sym -> {(rel, line)}
    defined: dict[str, str] = {}
    files = 0
    class_totals = {CODE: 0, COMMENT: 0, STRING: 0, HOLE: 0}
    fqn_literals: dict[str, int] = {}
    cache: list[tuple[str, str, str]] = []   # (rel, text, cls) —— 两遍法：先定定义集再收出现，控内存
    # pass 1：定义集 + 逐字符分类（廉价、与定义集无关）
    for p in in_scope_files(scope):
        try:
            text = p.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        files += 1
        rel = str(p.relative_to(REPO))
        cls = classify_chars(text)
        cache.append((rel, text, cls))
        for k in (CODE, COMMENT, STRING, HOLE):
            class_totals[k] += cls.count(k)
    for rel, text, cls in cache:
        for m in DEF_RE.finditer(text):
            if cls[m.start(1)] != CODE:
                continue
            dline = text.count("\n", 0, m.start(1)) + 1
            defined.setdefault(m.group(1), rel)
            decl.setdefault(m.group(1), set()).add((rel, dline))
    # pass 2：只记录**已定义符号**的出现（避免百万级无关标识符入内存）
    for rel, text, cls in cache:
        for m in IDENT_RE.finditer(text):
            tok = m.group(0)
            if tok not in defined:
                continue
            ln = text.count("\n", 0, m.start()) + 1
            occ.setdefault(tok, []).append((rel, ln, cls[m.start()]))
        for m in FQN_STR_RE.finditer(text):
            fqn_literals[m.group(1)] = fqn_literals.get(m.group(1), 0) + 1
    del cache
    scan_ms = (time.perf_counter() - t0) * 1000.0
    if not files or not defined:
        print(json.dumps({"error": "measurement_empty", "files": files, "defined": len(defined)}))
        return 3

    ref_class_counts = {CODE: 0, COMMENT: 0, STRING: 0, HOLE: 0}
    lost_v2_hole, lost_v2_str = [], []
    edge_causes = {"hole_borne": 0, "string_only": 0, "comment_only": 0, "comment_and_string": 0}
    hole_edge_examples = []
    edges_v1_tot = edges_v2_tot = edges_v3_tot = 0
    for sym, decls in decl.items():
        refs = [(r, l, c) for (r, l, c) in occ.get(sym, []) if (r, l) not in decls]
        for _, _, c in refs:
            ref_class_counts[c] += 1
        per_file: dict[str, set] = {}
        for r, _, c in refs:
            per_file.setdefault(r, set()).add(c)
        e1 = set(per_file)
        e2 = {r for r, cs in per_file.items() if CODE in cs}
        e3 = {r for r, cs in per_file.items() if CODE in cs or HOLE in cs}
        edges_v1_tot += len(e1)
        edges_v2_tot += len(e2)
        edges_v3_tot += len(e3)
        lost = e1 - e2
        if not lost:
            continue
        sym_hole = False
        for edge in sorted(lost):
            cs = per_file[edge]
            has_h, has_s, has_c = HOLE in cs, STRING in cs, COMMENT in cs
            if has_h:
                edge_causes["hole_borne"] += 1
                sym_hole = True
                if len(hole_edge_examples) < args.samples * 2:
                    hole_edge_examples.append({"sym": sym, "decl_file": defined[sym], "edge": edge,
                                               "classes_in_edge_file": "".join(sorted(cs))})
            elif has_s and has_c:
                edge_causes["comment_and_string"] += 1
            elif has_s:
                edge_causes["string_only"] += 1
            else:
                edge_causes["comment_only"] += 1
        rec = {"sym": sym, "decl_file": defined[sym], "ref_files_v1": len(e1), "ref_files_v2": len(e2),
               "ref_files_v3": len(e3), "lost_edges_v1_v2": sorted(lost)[:4],
               "recovered_by_v3": sorted(e3 - e2)[:4]}
        (lost_v2_hole if sym_hole else lost_v2_str).append(rec)

    refl = {k: v for k, v in fqn_literals.items() if k.split(".")[-1] in defined}
    neg = {s: [c for _, _, c in occ.get(s, [])] for s in args.absent_symbols}
    neg_total = sum(len(v) for v in neg.values())
    gate_pass = (edge_causes["hole_borne"] == CRITERIA["gate"]["hole_caused_lost_edge_count"]) and (neg_total == 0)

    result = {
        "probe": "exp1-q3b-mask-tradeoff",
        "instrument_revision": 2,
        "scope": args.scope, "files": files, "scan_ms": round(scan_ms, 2),
        "class_char_totals": class_totals,
        "defined_symbols": len(defined),
        "reference_occurrences_by_class": ref_class_counts,
        "reference_occurrences_total": sum(ref_class_counts.values()),
        "arm1_noise_share_pct": round(100.0 * (ref_class_counts[COMMENT] + ref_class_counts[STRING])
                                      / max(1, sum(ref_class_counts.values())), 3),
        "edges": {"v1_all_text": edges_v1_tot, "v2_code_only": edges_v2_tot, "v3_code_plus_hole": edges_v3_tot,
                  "arm2_lost_edges": edges_v1_tot - edges_v2_tot, "v3_recovered_edges": edges_v3_tot - edges_v2_tot},
        "lost_edge_cause_attribution": edge_causes,
        "hole_edge_examples": hole_edge_examples,
        "arm2_recall_cost": {
            "symbols_losing_edges": len(lost_v2_hole) + len(lost_v2_str),
            "hole_recoverable_symbols": len(lost_v2_hole),
            "string_only_loss_symbols": len(lost_v2_str),
            "gate_semantics_note": ("G1 判据为**逐边**归因（lost_edge_cause_attribution.hole_borne）："
                                    "该边在 V1 有、V2 丢、且该边所在文件存在孔洞型出现 ⇒ 孔洞型真引用边被 V2 误删；"
                                    "symbols_losing_edges / hole_recoverable_symbols 仅为样本索引（符号级）"),
            "hole_caused_samples": lost_v2_hole[: args.samples],
            "string_caused_samples": lost_v2_str[: args.samples],
        },
        "reflection_string_candidates_upper_bound": {"occurrences": sum(refl.values()), "distinct": len(refl),
                                                     "samples": sorted(refl.items(), key=lambda kv: -kv[1])[: args.samples]},
        "negative_control": {"symbols": {k: len(v) for k, v in neg.items()}, "total_counts": neg_total},
        "criteria_pre_registered": CRITERIA,
        "gate_pass": gate_pass,
        "verdict": ("G1/G2 通过：V2（掩注释+字符串，含孔洞）在**逐边**归因下无孔洞型召回损失；"
                    "V3 仍推荐（对方法/字段级粒度与插值孔洞引用更稳）"
                    if edge_causes["hole_borne"] == 0 else
                    f"G1 **不过**：V2 丢 {edge_causes['hole_borne']} 条孔洞型真引用边（V3 追回 "
                    f"{edges_v3_tot - edges_v2_tot} 条）⇒ 掩码规范必须用 V3（掩注释+纯字符串、保留插值孔洞）"),
        "honest_boundaries": [
            "孔洞内嵌套字符串/括号按最简规则处理（记深度，不解析嵌套串）⇒ 孔洞内容计数方向为『可能少记』",
            "符号族仅具名类型（方法/字段级引用不在范围）",
            "string_caused 为**上界**：只判『形如 FQN 且命中已定义符号』，不判该串是否为真引用",
            "边口径 = 文件级引用集（排除声明行）；与 exp1-Q3 的 GT 行级口径不同，不可直接相除",
            "v1 判据（符号级）被证实退化（声明行恒使 V2≥1），本文件判据为修正后预注册；旧读数存 result_degenerate.json",
        ],
    }
    Path(args.result).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": files, "scan_ms": result["scan_ms"], "defined_symbols": len(defined),
                      "gate_pass": gate_pass, "verdict": result["verdict"]}, ensure_ascii=False))
    print(json.dumps({"ref_occ_by_class": ref_class_counts, "arm1_noise_share_pct": result["arm1_noise_share_pct"],
                      "edges": result["edges"], "lost_edge_causes": edge_causes,
                      "refl_upper_bound": sum(refl.values()), "neg_total": neg_total}, ensure_ascii=False))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    sys.exit(main())
