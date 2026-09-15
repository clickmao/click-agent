#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q14 · L.7#2 「两条真候选人工复核」机械化 (通用代码逻辑)。

语言无关纪律 (用户 R447 钦定): 本文件不硬编码任何语言/工具后缀 —— 语料面、语言集、
文档后缀均由既有探针源码/常量派生; 输出名同样以码点拼接。

输入 (只读归档, 不重扫语料 ⇒ 不改测量对象):
  eval/capability/exp1-q10/attribution_q10.json
输出:
  prereg_q14.json / verdict_q14.json / evidence_q14.txt / selftest_q14.json
退出码: 0 全过 / 2 判据失败 / 3 测量或环境失败
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from collections import defaultdict

DOT = chr(46)
Q = pathlib.Path(__file__).resolve().parent
ROOT = Q.parents[2]
ARCH = ROOT / "eval" / "capability" / "exp1-q10" / ("attribution_q10" + DOT + "json")
PROBE = ROOT / "eval" / "capability" / "exp1-q10" / ("probe_v260" + DOT + "py")

REAL_RUNG = "noncode_mention"      # 归档档位取值 (数据, 非本文件自造)
OK_VERDICT = "ok"                  # 归档判决取值: 路径存在 ∧ 符号在被引位置以非代码形态出现
RETIRE_EXTRA = ("已消除", "已移除", "已废弃", "不再存在", "已下线", "已淘汰")
REG_MARKERS = ("延后", "待办", "未实现", "不存在", "漂移", "已修", "已删", "承诺")
PRIO = ["declared_ok", "retired_trace_same_line", "registered_promise_drift",
        "unregistered_promise_drift", "code_mention_unresolved"]
POS_CTRL = ("IResponseSegmentPlugin", "CapabilityScanner", "PythonArtifactPlugin")
NEG_CTRL = ("NoSuchTypeZzq9Xx", "RegistryThatNeverExistedZq")
WRAP = (0, 60)                     # 同一行内「符号 ↔ 留痕标记」的行级窗口 (只查同行)


def load_probe():
    spec = importlib.util.spec_from_file_location("probe_v260", str(PROBE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_lang(P):
    """语言集/语料面/后缀全部派生; 本文件零后缀字面量。"""
    cg = P.CODE_GLOBS[0]
    dg = P.DOC_GLOBS[0]
    return {"code_globs": list(P.CODE_GLOBS), "doc_globs": list(P.DOC_GLOBS),
            "code_ext": sorted(P.CODE_EXT), "strippable": list(P.STRIPPABLE_EXT),
            "retired_markers": list(P.RETIRED_MARKERS),
            "code_dir": cg.split("/")[0], "code_suffix": cg.rsplit(DOT, 1)[-1],
            "doc_suffix": dg.rsplit("/", 1)[-1].rsplit(DOT, 1)[-1]}


_CODE_ONLY_CACHE = {}


def code_only(P, repo, rel):
    """注释置空、字符串保留 ⇒ 字面量与构造实参可在**带行号**的代码面上匹配。逐文件缓存。"""
    if rel in _CODE_ONLY_CACHE:
        return _CODE_ONLY_CACHE[rel]
    raw = text_of(repo, rel)
    face = repo.codeface(rel) or ""
    face_lines = face.splitlines()
    keep = []
    for i, line in enumerate(raw.splitlines()):
        f = face_lines[i] if i < len(face_lines) else ""
        keep.append(line if f.strip() else "")
    _CODE_ONLY_CACHE[rel] = "\n".join(keep)
    return _CODE_ONLY_CACHE[rel]


def text_of(repo, rel):
    t, _ = repo.read(rel)
    return t or ""


def derive_candidates(P, repo, arch):
    """选择子 = 归档 rung==REAL_RUNG ∧ 归档 verdict==OK_VERDICT, 再机检三项前提:
    ① 命名形态非下划线分隔式; ② **树内**零声明; ③ 树内**仅**非代码形态出现 (纯注释)。
    三项与归档判决为**两路独立来源** (归档判决 vs 本处重算), 双方一致才入选; 不一致者单列。"""
    rows, part = [], {"rung_ok": 0, "accepted": 0, "rejected_naming": 0, "rejected_decl_or_codeface": 0}
    for c in arch["symbol_face_candidates"]:
        if c.get("rung") != REAL_RUNG or c.get("verdict") != OK_VERDICT:
            continue
        part["rung_ok"] += 1
        rel, sym = c["resolved"], c["symbol"]
        decl, _ = census(P, repo, sym, {"code_globs": list(P.CODE_GLOBS)})
        pure = set(decl) <= {"noncode_mention"} and decl.get("noncode_mention", 0) > 0
        zero = decl.get("declared_type", 0) + decl.get("declared_member", 0) == 0
        naming = "_" not in sym.strip("_")
        doc_text = text_of(repo, c["doc"])
        lines = doc_text.splitlines()
        doc_line = lines[c["doc_line"] - 1] if 0 <= c["doc_line"] - 1 < len(lines) else ""
        toks = [t for (_, _, t) in P._symbol_tokens(doc_line)]
        ok = naming and pure and zero
        if not ok:
            part["rejected_naming" if not naming else "rejected_decl_or_codeface"] += 1
            continue
        part["accepted"] += 1
        rows.append(dict(c, cross={"path_exists": repo.exists(rel), "doc_line_has_token": sym in toks,
                                   "tree_decl_zero": zero, "noncode_only": pure,
                                   "agrees": repo.exists(rel) and sym in toks},
                         doc_line_text=doc_line.strip()[:180], naming_ok=naming))
    return rows, part


def census(P, repo, sym, cfg):
    out, occ = defaultdict(int), []
    for g in cfg["code_globs"]:
        for rel in repo.glob(g):
            full = text_of(repo, rel)
            if not full or not re.search(r"\b" + re.escape(sym) + r"\b", full):
                continue
            face = repo.codeface(rel)
            out[P.symbol_face(sym, face, full)] += 1
            face_lines = (face or "").splitlines()
            for ln, line in enumerate(full.splitlines(), 1):
                if not re.search(r"\b" + re.escape(sym) + r"\b", line):
                    continue
                fl = face_lines[ln - 1] if ln - 1 < len(face_lines) else ""
                occ.append({"rel": rel, "line": ln, "text": line.strip()[:180],
                            "in_code_face": bool(re.search(r"\b" + re.escape(sym) + r"\b", fl))})
    return dict(out), occ


def occ_count(P, repo, sym, cfg):
    """出现**次数**口径 (与归档 symbol_occurrences 同口径: 匹配行数)。"""
    n = 0
    for g in cfg["code_globs"]:
        for rel in repo.glob(g):
            full = text_of(repo, rel)
            if full:
                n += len(re.findall(r"\b" + re.escape(sym) + r"\b", full))
    return n


def retirement_traces(sym, occ, markers):
    """留痕判据: 标记与符号**同一行** (跨行标记常指向别的对象 ⇒ 误判, 见夹具 trap 格)。"""
    return [o for o in occ if not o["in_code_face"] and any(m in o["text"] for m in markers)]


def registrations_elsewhere(P, repo, sym, exclude_sites, markers, cfg):
    """树内**该引用行之外**是否已登记该符号: 文档语料里提该符号 ∧ 同行含登记类标记。"""
    hits = []
    for g in cfg["doc_globs"]:
        for rel in repo.glob(g):
            full = text_of(repo, rel)
            if not full or sym not in full:
                continue
            for ln, line in enumerate(full.splitlines(), 1):
                if sym not in line:
                    continue
                if not any(m in line for m in markers):
                    continue
                if (rel, ln) in exclude_sites:
                    continue
                hits.append({"doc": rel, "line": ln, "text": line.strip()[:180],
                             "same_doc_as_citation": rel in {s[0] for s in exclude_sites}})
    return hits


def classify(row, decl, traces, regs):
    if not row["cross"]["path_exists"]:
        return "waived"
    if decl.get("declared_type", 0) + decl.get("declared_member", 0) > 0:
        return "declared_ok"
    if traces:
        return "retired_trace_same_line"
    if regs:
        return "registered_promise_drift"
    return "unregistered_promise_drift"


# ------------------------------------------------- 死分支机检: 文件内「可生产性」
CTOR_RE = r"new\s+[A-Za-z_][A-Za-z0-9_]*\s*\("
EQ_LIT_RE = r'==\s*"([^"]*)"'


def balanced_args(text, open_paren_idx):
    depth, i, n = 0, open_paren_idx, len(text)
    while i < n:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren_idx + 1:i]
        i += 1
    return ""


def dead_branch_facts(P, repo, rel):
    """机检两事实: ①比较表达式字面量在本文件的**全部**出现是否只在比较处;
    ②本文件构造点实参字面量集合 (该值在本文件内唯一的可生产来源)。"""
    code = code_only(P, repo, rel)
    cmp_lits = sorted(set(re.findall(EQ_LIT_RE, code)))
    ctor_lits = sorted(set(re.findall(r'"([^"]*)"', " ".join(
        balanced_args(code, m.end() - 1) for m in re.finditer(CTOR_RE, code)))))
    facts = []
    for lit in cmp_lits:
        sites = [ln for ln, line in enumerate(code.splitlines(), 1) if ('"' + lit + '"') in line]
        cmp_sites = [ln for ln, line in enumerate(code.splitlines(), 1)
                     if lit in re.findall(EQ_LIT_RE, line)]
        facts.append({"literal": lit, "all_sites": sites, "cmp_sites": cmp_sites,
                      "only_comparisons": sites == cmp_sites, "producible_in_file": lit in ctor_lits,
                      "dead_in_file": (sites == cmp_sites) and (lit not in ctor_lits)})
    return {"rel": rel, "ctor_lits": ctor_lits, "facts": facts,
            "dead_literals": [f["literal"] for f in facts if f["dead_in_file"]]}


def corpus_literal_sites(P, repo, cfg, lit):
    hits = []
    for g in cfg["code_globs"]:
        for rel in repo.glob(g):
            code = code_only(P, repo, rel)
            for ln, line in enumerate(code.splitlines(), 1):
                if ('"' + lit + '"') in line:
                    hits.append({"rel": rel, "line": ln, "text": line.strip()[:150],
                                 "inside_ctor_args": bool([1 for m in re.finditer(CTOR_RE, code)
                                                           if ('"' + lit + '"') in balanced_args(code, m.end() - 1)])})
    return hits


# ------------------------------------------------- 夹具自检 (两侧样例 + 优先级判别对)
def _w(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def build_fixtures(P, tmp, cfg):
    fx = pathlib.Path(tmp)
    ext, dxt = cfg["code_suffix"], cfg["doc_suffix"]
    src = fx / cfg["code_dir"] / ("a" + DOT + ext)
    _w(src, "\n".join([
        "// DeclaredThing 在本行给出声明",
        "class DeclaredThing { }",
        "// PromiseThing 由宿主在启动时登记",
        "// RegisteredThing 由宿主在启动时登记",
        "// TracedThing 实例字段已消除",
        "// TrapThing 由宿主在启动时登记",
        "// 上句所说的反射扫描已删除",
        "class Box { public string Source; public Box(string s) { Source = s; } }",
        'void Mk() { var b = new Box("path"); if (b.Source == "assembly") { var q = 1; } }',
        'void Mk2() { var b = new Box("assembly"); if (b.Source == "assembly") { var q = 1; } }',
    ]) + "\n")
    cite = fx / "docs" / ("hist" + DOT + dxt)
    _w(cite, "| RegisteredThing | 由宿主登记 |\n| TracedThing | 实例字段已消除 |\n")
    _w(fx / "docs" / ("REG" + DOT + dxt),
       "| RegisteredThing | 未实现, 延后处理 |\n| TracedThing | 已修; 延后复核 |\n")
    rel_src = (cfg["code_dir"] + "/" + "a" + DOT + ext)
    rel_cite = "docs/" + "hist" + DOT + dxt
    mk = lambda s, dl: {"doc": rel_cite, "doc_line": dl, "resolved": rel_src, "symbol": s,
                        "rung": REAL_RUNG, "verdict": OK_VERDICT,
                        "cross": {"path_exists": True}}
    cases = {"declared": mk("DeclaredThing", 1), "promise_unreg": mk("PromiseThing", 1),
             "promise_reg": mk("RegisteredThing", 1), "traced": mk("TracedThing", 2),
             "trap_adjacent": mk("TrapThing", 1)}
    gone = dict(mk("GoneThing", 1), resolved=cfg["code_dir"] + "/" + "nope" + DOT + ext,
                cross={"path_exists": False})
    cases["missing_path"] = gone
    return cases


def run_fixtures(P, cfg):
    tmp = tempfile.mkdtemp(prefix="q14fx_")
    res = {}
    try:
        cases = build_fixtures(P, tmp, cfg)
        repo = P.Repo(pathlib.Path(tmp))
        markers = list(cfg["retired_markers"]) + list(RETIRE_EXTRA)
        sites = {(r["doc"], r["doc_line"]) for r in cases.values()}
        for name, row in cases.items():
            decl, occ = census(P, repo, row["symbol"], cfg)
            tr = retirement_traces(row["symbol"], occ, markers)
            regs = registrations_elsewhere(P, repo, row["symbol"], sites, REG_MARKERS, cfg)
            res[name] = {"class": classify(row, decl, tr, regs), "traces": len(tr), "regs": len(regs)}
        # 优先级置换判别对: traced 同时具备留痕与他处登记 ⇒ 类别随顺序翻转 (顺序非装饰)
        row = cases["traced"]
        decl, occ = census(P, repo, "TracedThing", cfg)
        tr = retirement_traces("TracedThing", occ, markers)
        regs = registrations_elsewhere(P, repo, "TracedThing", sites, REG_MARKERS, cfg)

        def cls_with(order):
            if decl.get("declared_member", 0) + decl.get("declared_type", 0) > 0:
                return "declared_ok"
            for c in order:
                if c == "retired_trace_same_line" and tr:
                    return c
                if c == "registered_promise_drift" and regs:
                    return c
            return "unregistered_promise_drift"

        res["prio_swap"] = {"a": cls_with(["registered_promise_drift", "retired_trace_same_line"]),
                            "b": cls_with(["retired_trace_same_line", "registered_promise_drift"])}
        db = dead_branch_facts(P, repo, cases["declared"]["resolved"])
        res["dead_branch"] = {"dead_literals": db["dead_literals"], "ctor_lits": db["ctor_lits"]}
        # 正/负控 (夹具面): 计数器不得恒 0 也不得恒真
        pos, _ = census(P, repo, "DeclaredThing", cfg)
        neg, _ = census(P, repo, "NoSuchZzFixture", cfg)
        res["counter"] = {"pos": sum(pos.values()), "neg": sum(neg.values())}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    expect = {"declared": "declared_ok", "promise_unreg": "unregistered_promise_drift",
              "promise_reg": "registered_promise_drift", "traced": "retired_trace_same_line",
              "trap_adjacent": "unregistered_promise_drift", "missing_path": "waived"}
    res["expected"] = expect
    res["pass"] = (all(res.get(k, {}).get("class") == v for k, v in expect.items())
                   and res["prio_swap"]["a"] != res["prio_swap"]["b"]
                   and res["dead_branch"]["dead_literals"] == []
                   and res["counter"]["pos"] >= 1 and res["counter"]["neg"] == 0)
    return res


def main():
    if not ARCH.exists() or not PROBE.exists():
        print("MEASURE_FAIL: 归档/探针缺失")
        return 3
    P = load_probe()
    cfg = derive_lang(P)
    fx = run_fixtures(P, cfg)
    (Q / ("selftest_q14" + DOT + "json")).write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
    if not fx["pass"]:
        print("SELFTEST_FAIL: 判定器不自证可信, 先修判定器")
        return 3

    arch = json.loads(ARCH.read_text(encoding="utf-8"))
    repo = P.Repo(ROOT)
    rows, part = derive_candidates(P, repo, arch)
    sites = {(r["doc"], r["doc_line"]) for r in rows}
    seen_dead = set()
    markers = list(cfg["retired_markers"]) + list(RETIRE_EXTRA)
    v = {"stage": "EXP1-Q14",
         "selector": "归档 rung==%s ∧ verdict==%s ∧ 非下划线式命名 ∧ 树内零声明 ∧ 仅非代码形态" % (
             REAL_RUNG, OK_VERDICT),
         "partition": part, "n_rows": len(rows), "n_symbols": len({r["symbol"] for r in rows}),
         "n_symbol_faces_archived": arch["n_symbol_faces"], "rungs_archived": arch["symbol_face_rungs"],
         "candidates": [], "classes": defaultdict(int), "dead_branch": [],
         "input_fingerprints": {}, "exit": 0}
    for r in rows:
        decl, occ = census(P, repo, r["symbol"], cfg)
        tr = retirement_traces(r["symbol"], occ, markers)
        # 排除面 = 本行自身的引用位置 (他行同符号的引用位置**算**他处登记, 这正是"已在他处登记"的证据)
        regs = registrations_elsewhere(P, repo, r["symbol"], {(r["doc"], r["doc_line"])}, REG_MARKERS, cfg)
        cls = classify(r, decl, tr, regs)
        v["classes"][cls] += 1
        v["candidates"].append({"symbol": r["symbol"], "doc": r["doc"], "doc_line": r["doc_line"],
                                "resolved": r["resolved"], "class": cls, "decl_census": decl,
                                "occurrences": occ, "traces": tr, "registrations_elsewhere": regs,
                                "cross": r["cross"], "doc_line_text": r.get("doc_line_text", "")})
        if cls in ("registered_promise_drift", "unregistered_promise_drift") and repo.exists(r["resolved"]):
            db = dead_branch_facts(P, repo, r["resolved"])
            for f in db["facts"]:
                if f["dead_in_file"] and (db["rel"], f["literal"]) not in seen_dead:
                    seen_dead.add((db["rel"], f["literal"]))
                    v["dead_branch"].append({"rel": db["rel"], "literal": f["literal"],
                                             "all_sites": f["all_sites"], "cmp_sites": f["cmp_sites"],
                                             "ctor_lits": db["ctor_lits"],
                                             "corpus_sites": corpus_literal_sites(P, repo, cfg, f["literal"])})
    v["classes"] = dict(v["classes"])
    v["dispositions"] = {
        "retired_trace_same_line": "文档时效(历史快照; 符号已退役且有同行留痕) ⇒ 非引用图缺陷; 可选动作=给快照行补修复留痕",
        "registered_promise_drift": "注释承诺无实现(树内零声明) ∧ 他处已登记 ⇒ 归口既有登记, 非引用图缺陷; 新增精度事实=文件内不可生产字面量",
        "unregistered_promise_drift": "尚未登记 ⇒ 需移交(本轮该类为零, 单列)",
        "declared_ok": "树内有声明 ⇒ 非缺陷",
        "waived": "测量面不可解析/路径歧义 ⇒ 弃权单列, 不判红",
    }
    # 计数交叉核对 (同口径 = 出现次数): 与归档 symbol_occurrences 逐符号比对 + 正负控非退化
    arch_occ = arch.get("symbol_occurrences", {})
    occ_pos = {s: occ_count(P, repo, s, cfg) for s in POS_CTRL}
    occ_neg = {s: occ_count(P, repo, s, cfg) for s in NEG_CTRL}
    occ_cand = {s: occ_count(P, repo, s, cfg) for s in sorted({r["symbol"] for r in rows})}
    same, not_comparable = {}, []
    for s in list(POS_CTRL) + list(NEG_CTRL) + list(occ_cand):
        if s not in arch_occ:
            not_comparable.append(s)
            continue
        mine = {**occ_pos, **occ_neg, **occ_cand}.get(s)
        same[s] = (mine == arch_occ.get(s))
    v["counter"] = {"caliber": "occurrence_count", "positive": occ_pos, "negative": occ_neg,
                    "candidates": occ_cand,
                    "archive": {k: arch_occ.get(k) for k in list(occ_pos) + list(occ_neg) + list(occ_cand)},
                    "same_caliber_equal": same, "not_comparable": not_comparable,
                    "nondegenerate": all(n >= 1 for n in occ_pos.values()) and all(n == 0 for n in occ_neg.values()),
                    "file_caliber_positive": {s: sum(census(P, repo, s, cfg)[0].values()) for s in POS_CTRL}}
    checks = {
        "P1_partition_conserved": part["rung_ok"] == part["accepted"] + part["rejected_naming"] + part["rejected_decl_or_codeface"],
        "P2_three_rows_two_symbols": len(rows) == 3 and v["n_symbols"] == 2,
        "P3_conservation": sum(v["classes"].values()) == len(rows) and len(rows) >= 2,
        "P4_nontrivial": len([k for k, n in v["classes"].items() if n > 0]) >= 2,
        "P5_cross_agrees": all(r["cross"]["agrees"] for r in v["candidates"]),
        "P6_no_declared_for_promise": all(
            c["decl_census"].get("declared_type", 0) + c["decl_census"].get("declared_member", 0) == 0
            for c in v["candidates"]),
        "P7_counter_same_caliber": all(same.values()) and v["counter"]["nondegenerate"],
        "P8_dead_branch_found": len(v["dead_branch"]) >= 1,
        "P9_fixtures_and_prio": fx["pass"] and fx["prio_swap"]["a"] != fx["prio_swap"]["b"],
        "P10_dispositions_complete": all(c in v["dispositions"] for c in set(v["classes"]) | {"waived"}),
    }
    body = json.dumps({k: v[k] for k in ("candidates", "classes", "dead_branch", "counter")},
                      ensure_ascii=False, sort_keys=True)
    v["output_sha"] = hashlib.sha256(body.encode()).hexdigest()
    for rel in sorted({r["doc"] for r in rows} | {r["resolved"] for r in rows}):
        _, sha = repo.read(rel)
        v["input_fingerprints"][rel] = sha
    v["checks"] = checks
    if not all(checks.values()):
        v["exit"] = 2
    (Q / ("prereg_q14" + DOT + "json")).write_text(json.dumps(
        {"criteria": checks, "class_priority": PRIO, "retired_markers": markers, "reg_markers": list(REG_MARKERS),
         "selector": v["selector"], "line_window": WRAP}, ensure_ascii=False, indent=1), encoding="utf-8")
    (Q / ("verdict_q14" + DOT + "json")).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["EXP1-Q14 真候选复核 · 行=%d 符号=%d 类分布=%s 弃权=%d" % (
        len(rows), v["n_symbols"], v["classes"], v["classes"].get("waived", 0))]
    for c in v["candidates"]:
        L.append("  - %s @ %s:%d -> %s :: %s" % (c["symbol"], c["doc"], c["doc_line"], c["resolved"], c["class"]))
        L.append("    形态=%s 出现=%s" % (c["decl_census"], [(o["rel"], o["line"]) for o in c["occurrences"]]))
        L.append("    留痕=%d 他处登记=%d 交叉=%s" % (len(c["traces"]), len(c["registrations_elsewhere"]), c["cross"]))
        for g in c["registrations_elsewhere"][:3]:
            L.append("      登记: %s:%d %s" % (g["doc"], g["line"], g["text"][:110]))
        L.append("    引用行: %s" % c["doc_line_text"][:140])
    for d in v["dead_branch"]:
        L.append("  ! 文件内不可生产字面量 %s @ %s 出现行=%s 比较行=%s 构造实参=%s" % (
            d["literal"], d["rel"], d["all_sites"], d["cmp_sites"], d["ctor_lits"]))
        for s in d["corpus_sites"][:3]:
            L.append("      语料他处: %s:%d %s (构造实参内=%s)" % (s["rel"], s["line"], s["text"][:100],
                                                                  s["inside_ctor_args"]))
    L.append("counter=%s" % json.dumps(v["counter"], ensure_ascii=False)[:220])
    L.append("checks=%s sha=%s" % (checks, v["output_sha"][:16]))
    (Q / ("evidence_q14" + DOT + "txt")).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return v["exit"]


if __name__ == "__main__":
    sys.exit(main())
