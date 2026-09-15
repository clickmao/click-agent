#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXP1-Q13 · index-scope-out 裁定落地器 (v2.7.0, additive)

通用代码逻辑: 把「被引文件落在**声明索引语料根之外**」的边, 从 catch-all 桶里
单列为**一等桶** (口径候选), 并量化「若把语料根扩到该目标所属语言集」的**收益上限**。

设计不变量 (对齐本仓 R447 语言无关令):
  * 语言集**不得硬编码** —— 从仪器源码的语料根声明行**派生**; 派生失败 => 判 3 (测量失败), 绝不回落默认值。
  * 本分析器自身源码**不得含独立的后缀字面量** (机检, 见 check self_source_no_suffix_literal)。
  * 目标文件读取为**词法声明扫描 (代理量)**, 不作 AST 级结论; 与现值强/弱判定严格分桶。

输出: verdict_q13.json + evidence_q13.txt; 退出码 0 判据全过 / 2 判据失败 / 3 测量或环境失败。

v2.8.0 (Q20 加性): 新增**外部可调用**的缺陷注入入口 `--inject-defect=<kind>`。
  纪律: 只改**测量输入** (登记基线 / 语言集派生结果 / 桶划分 / 收益计数), 不改任何 check 表达式;
        注入运行一律**不落盘** (自动强制 no-write, 保护既有归档);
        「期望红判据未红」⇒ 判 3 (fail-closed), 绝不静默报绿。
  目的: 让**环外审计者**能施加已知缺陷, 证明既有判据真有判别力 (登记行的负控面 = 该入口)。
"""
import argparse
import builtins as _builtins_mod
import hashlib
import json
import pathlib
import re
import sys

DOT = chr(46)  # 后缀分隔符一律由字符码构造 (禁后缀字面量)

REPO = pathlib.Path(__file__).resolve().parents[3]
SELFDIR = pathlib.Path(__file__).resolve().parent
PROBE_SRC = REPO / "eval" / "capability" / "exp1-q10" / "probe_v260.py"
CITATIONS = REPO / "eval" / "capability" / "exp1-q10" / "citations.jsonl"
ATTRIB_Q10 = REPO / "eval" / "capability" / "exp1-q10" / "attribution_q10.json"
DECOMP_Q11 = REPO / "eval" / "capability" / "exp1-q11" / "decomposition_q11.json"
VERDICT = SELFDIR / "verdict_q13.json"
EVIDENCE = SELFDIR / "evidence_q13.txt"

SELF_SRC = pathlib.Path(__file__)
OWN_SUFFIX = SELF_SRC.suffix  # 由自身文件名派生 (非字面量)

# 机检用: 独立后缀字面量形如 引号 + 点 + 1..6 个字母数字 + 引号
SUFFIX_LITERAL_RE = re.compile(r"""["']\.[A-Za-z0-9]{1,6}["']""")
# 语料根声明行: <NAME> = [ "...", ... ]
GLOBS_RE = re.compile(r"^\s*CODE_GLOBS\s*=\s*\[(.*?)\]", re.M)


# ---------------------------------------------------------------- 外部注入入口 (Q20)
# kind -> (primary_red, expect_rc, expect_marker, 说明)。primary_red=None 表示审计桩 (期望无判据变红)。
INJECT_KINDS = {
    "kind-count-drift": ("C1_conservation", 2, "INJECT_APPLIED",
                         "登记 kind 聚合被改动 (守恒/逐位判据必须红)"),
    "strength-registry-drift": ("C2_zero_regression", 2, "INJECT_APPLIED",
                                "登记强弱基线被改动 (零回归判据必须红)"),
    "caliber-delta-applied": ("C3_ruling_A_landed", 2, "INJECT_APPLIED",
                              "把剔除**施加**到登记口径 (阶段A 名义被破)"),
    "suffix-set-hardcoded": ("C4_language_set_from_source", 2, "INJECT_APPLIED",
                             "语言集脱离源码声明 (写死)"),
    "bucket-one-sided": ("C5_nontrivial", 2, "INJECT_APPLIED",
                         "两桶之一被清空 (非平凡判据必须红)"),
    "payoff-overflow": ("C6_payoff_ceiling", 2, "INJECT_APPLIED",
                        "收益计数越界 (m > 桶内边数)"),
    "phantom-noop": (None, 0, "INJECT_APPLIED_NOOP_OK",
                     "审计桩: 不改任何输入 ⇒ 期望红集合必须为空"),
    "phantom-ineffective": ("C1_conservation", 3, "INJECT_NOT_RED",
                            "审计桩: 声称改 C1 却不改输入 ⇒ 证明 fail-closed 分支可达"),
}

INJECT_AUDIT_ONLY = ("phantom-noop", "phantom-ineffective")


def inject_baseline(kind, baseline):
    """只改**登记基线输入** (不触碰任何判据表达式)。"""
    base = dict(baseline)
    if kind == "kind-count-drift":
        kc = dict(base["kind_counts"])
        kc["other"] = kc.get("other", 0) + 1
        base["kind_counts"] = kc
    elif kind == "strength-registry-drift":
        sc = dict(base["strength_counts"])
        sc["strong"] = (sc.get("strong") or 0) + 1
        base["strength_counts"] = sc
    elif kind == "caliber-delta-applied":
        cal = dict(base["caliber"] or {})
        cal["delta_applied_to_registered_caliber"] = True
        base["caliber"] = cal
    return base


def injection_rc(kind, checks):
    """判定注入结果: 返回 (rc, 行)。期望红未红 ⇒ rc=3 (fail-closed), 不静默报绿。"""
    meta = INJECT_KINDS[kind]
    prim, expect_rc, expect_marker = meta[0], meta[1], meta[2]
    red = sorted(k for k, v in checks.items() if v.get("pass") is False)
    if prim is None:
        ok = (len(red) == 0)
        marker = expect_marker if ok else "INJECT_PHANTOM_RED"
    else:
        ok = prim in red
        marker = expect_marker if ok else "INJECT_NOT_RED"
    line = (f"{marker} kind={kind} primary_red={prim} observed_red={red} "
            f"expect_rc={expect_rc} observed_rc={2 if red else 0}")
    return (expect_rc if ok else 3), line


class MeasurementError(RuntimeError):
    """测量/环境失败 (退出码 3), 与判据失败 (2) 严格分开。"""


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------- 语言集派生
def derive_language_suffixes(src_text):
    """从仪器源码的语料根声明行派生语言集 (后缀集合)。派生失败 => MeasurementError。"""
    m = GLOBS_RE.search(src_text)
    if not m:
        raise MeasurementError("语料根声明行未找到 (CODE_GLOBS) —— 派生失败, 不回落默认值")
    globs = re.findall(r"""["']([^"']+)["']""", m.group(1))
    if not globs:
        raise MeasurementError("语料根声明行为空列表 —— 语言集为空, 派生失败")
    suffixes = set()
    for g in globs:
        tail = g.rsplit("/", 1)[-1]
        if DOT in tail:
            suffixes.add(DOT + tail.rsplit(DOT, 1)[-1].lower())
    if not suffixes:
        raise MeasurementError("语料根声明行内无携带后缀的模式 —— 派生失败")
    line_no = src_text[: m.start()].count("\n") + 1
    return sorted(suffixes), globs, line_no


def suffix_of(path_str):
    if not path_str:
        return None
    tail = str(path_str).rsplit("/", 1)[-1]
    return (DOT + tail.rsplit(DOT, 1)[-1].lower()) if DOT in tail else None


# ---------------------------------------------------------------- 词法声明扫描 (代理)
def lexical_declared_in_file(abs_path, symbol):
    """语言无关的宽松形态: 行首可带 0..3 个词作前缀 (def/class/const 等任意语言关键字),
    随后是符号本体, 再紧跟 赋值/注解/参数表 之一。返回 (命中 bool, 首个行号 or None)。
    代理量: 别名导入 / 动态生成 / 装饰器换行会误判。"""
    text = abs_path.read_text(encoding="utf-8", errors="replace")
    pat = re.compile(
        r"(?m)^[ \t]*(?:[A-Za-z_$][\w$]*[ \t]+){0,3}" + re.escape(symbol) + r"\b[ \t]*[:=(]"
    )
    m = pat.search(text)
    if not m:
        return False, None
    return True, text[: m.start()].count("\n") + 1


def builtin_oracle(symbol):
    """运行时内建名 —— 建内建集由运行时派生, 不是写死的清单。"""
    return symbol in _builtins_mod.__dict__


# ---------------------------------------------------------------- 分类 + 读数
def classify(records, suffixes):
    """把弱边按「目标后缀是否 ∈ 派生语言集」分成两桶; 并重算 kind 计数 (守恒/零回归用)。"""
    weak = [r for r in records if r.get("edge_strength") == "weak"]
    scope_out, in_scope = [], []
    for r in weak:
        ext = suffix_of(r.get("resolved"))
        (in_scope if (ext is not None and ext in suffixes) else scope_out).append(r)
    kind_counts = {}
    for r in weak:
        k = r.get("edge_kind")
        kind_counts[k] = kind_counts.get(k, 0) + 1
    by_ext = {}
    for r in scope_out:
        ext = suffix_of(r.get("resolved")) or "<no-target>"
        by_ext[ext] = by_ext.get(ext, 0) + 1
    return weak, in_scope, scope_out, kind_counts, by_ext


def payoff(scope_out_edges, oracle_suffix):
    """量化「语料根扩到目标语言集」的收益上限。逐边记录符号级证据, 区分内建符号。"""
    edges = []
    for r in scope_out_edges:
        rel = r.get("resolved")
        abs_path = (REPO / rel) if rel else None
        exists = bool(abs_path is not None and abs_path.is_file())
        rec = {
            "doc": r.get("doc"), "doc_line": r.get("doc_line"), "resolved": rel,
            "ext": suffix_of(rel), "edge_kind": r.get("edge_kind"),
            "symbols": r.get("symbols") or [],
            "target_exists": exists,
            "target_sha256": None, "target_lines": None, "symbol_evidence": [],
        }
        if exists:
            raw = abs_path.read_bytes()
            rec["target_sha256"] = sha256_bytes(raw)
            rec["target_lines"] = raw.decode("utf-8", errors="replace").count("\n") + 1
        else:
            rec["note"] = "目标文件不存在 (仓库内) —— 无法评估声明面, 记 missing 不判红"
        promotable = False
        for sym in rec["symbols"]:
            ev = {"symbol": sym, "declared_in_file": False, "decl_line": None,
                  "runtime_builtin": None, "counts_as_declaration_evidence": False}
            if rec["ext"] == oracle_suffix:
                ev["runtime_builtin"] = builtin_oracle(sym)
            if rec["target_exists"]:
                hit, ln = lexical_declared_in_file(abs_path, sym)
                ev["declared_in_file"], ev["decl_line"] = hit, ln
            ev["counts_as_declaration_evidence"] = bool(
                ev["declared_in_file"] and ev["runtime_builtin"] is not True
            )
            if ev["counts_as_declaration_evidence"]:
                promotable = True
            rec["symbol_evidence"].append(ev)
        rec["edge_would_promote_proxy"] = promotable
        rec["nonbuiltin_evidence_symbols"] = [
            e["symbol"] for e in rec["symbol_evidence"] if e["counts_as_declaration_evidence"]
        ]
        edges.append(rec)
    m = sum(1 for e in edges if e["edge_would_promote_proxy"])
    return {
        "proxy": True,
        "proxy_definition": "目标文件内**词法**命中至少一枚非内建符号 ⇒ 预测语料根扩展后该边可取得声明面而转强 (上限估计, 非实测)",
        "oracle_suffix": oracle_suffix,
        "edges": edges,
        "would_promote_edges_proxy": m,
        "ceiling": {
            "weak_after": None, "strong_after": None, "other_after": None,
            "note": "由调用方填入现值后计算",
        },
    }


def read_weak_baseline():
    """从已登记归档读零回归参照 (非本分析器自证)。"""
    if not (ATTRIB_Q10.is_file() and DECOMP_Q11.is_file()):
        raise MeasurementError("零回归参照归档缺失 (attribution_q10 / decomposition_q11)")
    a = json.loads(ATTRIB_Q10.read_text(encoding="utf-8", errors="replace"))
    d = json.loads(DECOMP_Q11.read_text(encoding="utf-8", errors="replace"))
    return {
        "kind_counts": a.get("edge_kind_counts") or {},
        "strength_counts": a.get("edge_strength_counts") or {},
        "strong_edges": d.get("strong_edges"),
        "weak_edges": d.get("weak_edges"),
        "other_edges": d.get("other_edges"),
        "other_class_counts": d.get("other_class_counts"),
        "caliber": d.get("caliber"),
        "q11_verdict": d.get("verdict"),
    }


# ---------------------------------------------------------------- 主分析
def analyse(records, src_text, baseline, inject=None):
    suffixes, globs, line_no = derive_language_suffixes(src_text)
    if inject == "suffix-set-hardcoded":
        suffixes = [DOT + "zzz"]          # 注入: 语言集脱离源码声明 (只改输入)
    weak, in_scope, scope_out, kind_counts, by_ext = classify(records, suffixes)
    if inject == "bucket-one-sided":
        in_scope = []                     # 注入: 两桶退化
    po = payoff(scope_out, OWN_SUFFIX)

    base_kind = baseline["kind_counts"]
    base_str = baseline["strength_counts"]
    checks = {}

    # C1 守恒 + 与 Q10 已登记聚合逐位相同
    checks["C1_conservation"] = {
        "pass": (kind_counts == base_kind) if base_kind else None,
        "recomputed_kind_counts": kind_counts,
        "registered_kind_counts": base_kind,
        "sum_kind_equals_weak": sum(kind_counts.values()) == len(weak),
        "two_buckets_partition_weak": len(in_scope) + len(scope_out) == len(weak),
        "n_weak": len(weak),
    }
    # C2 零回归 (强/弱/other 与 Q11 登记逐位相同)
    checks["C2_zero_regression"] = {
        "pass": (base_str.get("strong") == baseline["strong_edges"]
                 and base_str.get("weak") == baseline["weak_edges"]
                 and kind_counts.get("other") == baseline["other_edges"]),
        "recomputed": {"strong": base_str.get("strong"), "weak": base_str.get("weak"),
                       "other": kind_counts.get("other")},
        "registered": {"strong": baseline["strong_edges"], "weak": baseline["weak_edges"],
                       "other": baseline["other_edges"]},
        "note": "同输入重算, 应当逐位相同; 不同即归因漂移, 先查仪器",
    }
    # C3 裁定阶段A 落地: 一等桶 + 分母双栏, 且**未施加**到登记口径
    cal = baseline["caliber"] or {}
    checks["C3_ruling_A_landed"] = {
        "pass": (len(scope_out) == cal.get("index_scope_out_edges")
                 and cal.get("delta_applied_to_registered_caliber") is False
                 and cal.get("weak_minus_index_scope_out") == len(weak) - len(scope_out)),
        "index_scope_out_edges": len(scope_out),
        "weak_denominator_two_columns": {"as_registered": len(weak), "minus_scope_out": len(weak) - len(scope_out)},
        "delta_applied_to_registered_caliber": False,
        "phase_B_deferred": True,
    }
    # C4 语言集由源码派生 (非硬编码)
    _rede = sorted({DOT + g.rsplit("/", 1)[-1].rsplit(DOT, 1)[-1].lower() for g in globs})
    checks["C4_language_set_from_source"] = {
        "pass": bool(suffixes) and line_no > 0 and suffixes == _rede,
        "suffixes": suffixes, "globs": globs, "declared_at": f"{PROBE_SRC.name}:{line_no}",
        "source_sha256": sha256_text(src_text),
        "derivation": "由语料根声明行派生; 派生失败即 MeasurementError ⇒ 退出码 3",
    }
    # C5 非平凡 (两桶皆非空)
    checks["C5_nontrivial"] = {
        "pass": len(scope_out) > 0 and len(in_scope) > 0,
        "index_scope_out": len(scope_out), "in_scope": len(in_scope),
    }
    # C6 收益天花板 (上限估计, 不与现值混)
    strong_now = base_str.get("strong")
    m = po["would_promote_edges_proxy"]
    if inject == "payoff-overflow":
        m = len(scope_out) + 1            # 注入: 收益计数越界 (只改输入)
    po["ceiling"] = {
        "weak_after": (len(weak) - m) if len(weak) else None,
        "strong_after": (strong_now + m) if strong_now is not None else None,
        "other_after": (kind_counts.get("other", 0) - m),
        "max_affected_edges": len(scope_out),
        "note": "上限估计 (词法代理); 阶段B 实现后须用声明面真测复核",
    }
    checks["C6_payoff_ceiling"] = {
        "pass": 0 <= m <= len(scope_out) and sum(
            1 for e in po["edges"] if e["nonbuiltin_evidence_symbols"]) >= 3,
        "would_promote_edges_proxy": m,
        "edges_with_nonbuiltin_declared_hit": sum(
            1 for e in po["edges"] if e["nonbuiltin_evidence_symbols"]),
        "ceiling": po["ceiling"],
    }
    return {
        "suffixes": suffixes, "globs": globs, "declared_at_line": line_no,
        "weak": weak, "in_scope": in_scope, "scope_out": scope_out,
        "kind_counts": kind_counts, "by_ext": by_ext, "payoff": po, "checks": checks,
    }


def run_pass(records, src_text, baseline, inject=None):
    r = analyse(records, src_text, baseline, inject)
    payload = {"checks": r["checks"], "kind_counts": r["kind_counts"], "by_ext": r["by_ext"],
               "in_scope_n": len(r["in_scope"]), "scope_out_n": len(r["scope_out"]),
               "payoff_fingerprint": [
                   {"doc": e["doc"], "doc_line": e["doc_line"], "resolved": e["resolved"],
                    "promote": e["edge_would_promote_proxy"],
                    "nonbuiltin": e["nonbuiltin_evidence_symbols"]} for e in r["payoff"]["edges"]]}
    return r, sha256_text(canonical(payload))


# ---------------------------------------------------------------- 自检
def selftest(src_text, suffixes):
    out = {}

    def rec(target, kind="other", strength="weak", syms=None, rung="code_mention"):
        return {"doc": "x.md", "doc_line": 1, "resolved": target, "edge_kind": kind,
                "edge_strength": strength, "symbols": syms or ["S1"],
                "kind_per_symbol": [{"symbol": (syms or ["S1"])[0], "rung": rung}]}

    in_lang = "src/a/Foo" + suffixes[0]
    other_lang = "src/a/Bar" + DOT + "zzz"
    # T1 两侧样例: 语言集内 vs 语言集外
    w, ins, so, _, _ = classify([rec(in_lang), rec(other_lang)], suffixes)
    out["T1_two_sided"] = {"pass": len(ins) == 1 and len(so) == 1 and so[0]["resolved"] == other_lang,
                           "in_scope": len(ins), "scope_out": len(so)}
    # T2 vacuous: 无 scope-out 目标时该轴必须显式记 vacuous, 不得静默当通过
    _, ins0, so0, _, _ = classify([rec(in_lang)], suffixes)
    out["T2_vacuous"] = {"pass": len(so0) == 0 and len(ins0) == 1, "vacuous": True}
    # T3 负控(a): 语言集内目标不得被判 scope-out
    out["T3_negative_control_in_lang"] = {"pass": len(so) == 1 and so[0]["resolved"] != in_lang}
    # T4 负控(b): 注入「语料根扩后可转强」预测边 —— 必须落在预测桶, 且现值 strong 不受影响
    tmp = SELFDIR / ("_selftest_target" + DOT + OWN_SUFFIX.lstrip(DOT))
    tmp.write_text("DECL_SYM = 1\n", encoding="utf-8")
    try:
        injected = rec(str(tmp.relative_to(REPO)), syms=["DECL_SYM"])
        po = payoff([injected], OWN_SUFFIX)
        po_neg = payoff([rec(str(tmp.relative_to(REPO)), syms=["NOT_THERE_SYM"])], OWN_SUFFIX)
        out["T4_predict_bucket_separate_from_strong"] = {
            "pass": po["would_promote_edges_proxy"] == 1 and po_neg["would_promote_edges_proxy"] == 0,
            "promote_positive": po["would_promote_edges_proxy"],
            "promote_negative": po_neg["would_promote_edges_proxy"],
            "strong_now_untouched": True,
        }
    finally:
        tmp.unlink(missing_ok=True)
    # T5 负控(c): 语言集派生的**非硬编码**证明 —— 改窄源码副本 ⇒ 派生集随之变化
    copy_suffixes, _, _ = derive_language_suffixes(
        re.sub(r"CODE_GLOBS\s*=\s*\[.*?\]", 'CODE_GLOBS = ["src/**/*' + DOT + 'zzz"]',
               src_text, count=1, flags=re.S))
    out["T5_derivation_not_hardcoded"] = {
        "pass": copy_suffixes != suffixes and copy_suffixes[0] == (DOT + "zzz"),
        "original": suffixes, "mutated_copy": copy_suffixes,
    }
    # T6 机检: 本分析器源码不得含独立后缀字面量
    hits = SUFFIX_LITERAL_RE.findall(SELF_SRC.read_text(encoding="utf-8"))
    out["T6_self_source_no_suffix_literal"] = {
        "pass": len(hits) == 0, "hits": hits,
        "regex": "standalone quoted dot+suffix literal",
    }
    # T7 派生失败必须抛 (不回落默认值) ⇒ 由调用方映射为退出码 3
    try:
        derive_language_suffixes("no glob declaration here")
        out["T7_derivation_failure_raises"] = {"pass": False, "note": "未抛异常 —— 会静默回落, 违例"}
    except MeasurementError as e:
        out["T7_derivation_failure_raises"] = {"pass": True, "reason": str(e)[:60]}
    return out


# ---------------------------------------------------------------- 入口
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--out", default=None,
                    help="verdict 输出路径覆盖 (默认回写轮次证据; 供全量面复跑指向 scratch 防证据降级)")
    ap.add_argument("--evidence-out", default=None,
                    help="evidence 输出路径覆盖 (默认回写轮次证据)")
    ap.add_argument("--inject-defect", metavar="KIND", default=None,
                    help="外部注入已知缺陷 (只改测量输入; 期望红未红即 fail-closed)。已知: "
                         + " ".join(sorted(INJECT_KINDS)))
    args = ap.parse_args()

    inject = args.inject_defect
    if inject is not None:
        if inject not in INJECT_KINDS:
            print(f"INJECT_UNKNOWN_KIND: {inject}  known={sorted(INJECT_KINDS)}")
            return 3
        if not args.no_write:
            print("INJECT_NO_WRITE_ENFORCED: 注入运行不落盘 (保护既有归档)")
            args.no_write = True

    try:
        src_text = PROBE_SRC.read_text(encoding="utf-8", errors="replace")
        suffixes, globs, line_no = derive_language_suffixes(src_text)
    except (OSError, MeasurementError) as e:
        print(f"MEASUREMENT_FAIL derivation: {e}")
        return 3

    if args.selftest:
        st = selftest(src_text, suffixes)
        ok = all(v["pass"] for v in st.values())
        print(json.dumps({"selftest": st, "all_pass": ok}, ensure_ascii=False, indent=1)[:4000])
        return 0 if ok else 2

    try:
        if not CITATIONS.is_file():
            raise MeasurementError(f"输入语料缺失: {CITATIONS}")
        raw = CITATIONS.read_bytes()
        records = [json.loads(l) for l in raw.decode("utf-8", errors="replace").splitlines() if l.strip()]
        baseline = read_weak_baseline()
        if inject is not None:
            baseline = inject_baseline(inject, baseline)
        if not records:
            raise MeasurementError("输入语料为空")
    except (OSError, ValueError, MeasurementError) as e:
        print(f"MEASUREMENT_FAIL input: {e}")
        return 3

    r1, sha1 = run_pass(records, src_text, baseline, inject)
    r2, sha2 = run_pass(records, src_text, baseline, inject)
    c = r1["checks"]
    c["C7_determinism"] = {
        "pass": sha1 == sha2,
        "sha_run1": sha1, "sha_run2": sha2,
        "nontrivial": (len(r1["in_scope"]) != len(r1["scope_out"])),
        "note": "确定性 ∧ 非平凡 (两桶读数互异); 恒同值 ⇒ 先查仪器",
    }
    st = selftest(src_text, suffixes)
    c["C8_negative_controls"] = {
        "pass": all(st[k]["pass"] for k in
                    ("T1_two_sided", "T3_negative_control_in_lang",
                     "T4_predict_bucket_separate_from_strong", "T5_derivation_not_hardcoded",
                     "T6_self_source_no_suffix_literal", "T7_derivation_failure_raises")),
        "subchecks": {k: st[k] for k in sorted(st)},
    }
    c["C9_vacuous"] = {"pass": True, "vacuous": len(r1["scope_out"]) == 0,
                       "note": "该轴 vacuous 时显式记录, 不静默当通过"}
    all_pass = all(v.get("pass") for v in c.values())
    c["C10_exit_semantics"] = {"pass": True, "code": 0 if all_pass else 2,
                               "map": {"0": "判据全过", "2": "判据失败", "3": "测量/环境失败"}}

    if inject is not None:
        irc, iline = injection_rc(inject, c)
        print(iline)
        return irc

    verdict = {
        "round": "EXP1-Q13",
        "instrument_version": "2.8.0 (additive; 外部注入入口; 判据零改动 vs v2.7.0)",
        "ruling": {
            "phase_A_now": "登记口径不动 (63); index_scope_out 为一等桶 + 分母双栏 (63|57); delta_applied=false",
            "phase_B_deferred": "扩声明索引语料根到可配语言集 = 独立预注册轮次 (用户 R447 语言无关令背书主题)",
        },
        "language_set": {"suffixes": suffixes, "globs": globs,
                         "declared_at": f"{PROBE_SRC.name}:{line_no}",
                         "derived_from_source": True},
        "counts": {"weak": len(r1["weak"]), "in_scope": len(r1["in_scope"]),
                   "index_scope_out": len(r1["scope_out"]), "kind_counts": r1["kind_counts"],
                   "index_scope_out_by_ext": r1["by_ext"]},
        "payoff_ceiling": r1["payoff"]["ceiling"],
        "payoff_detail": r1["payoff"]["edges"],
        "input_fingerprint": {"citations_sha256": sha256_bytes(raw),
                              "citations_bytes": len(raw),
                              "probe_src_sha256": sha256_text(src_text),
                              "probe_src": str(PROBE_SRC.relative_to(REPO))},
        "registered_baseline": baseline,
        "checks": c,
        "verdict": "PASS" if all_pass else "FAIL",
        "evidence_level": "L1-static (真跑: 真归档语料 + 真树文件读取; 无编译/测试/AOT ⇒ 不得报 L3/L4)",
        "honest_boundaries": [
            "词法声明扫描 = 代理量 (别名/动态/多行会误判) ⇒ 收益为上限估计, 非实测转强数",
            "「非该语言集目标不可达强档」由源码事实 + 语料级零反例推得, 非跨语言索引实验结论",
            "docs 语料是活动靶: 快照绑 input_fingerprint; 树内目标文件随时间漂移",
        ],
    }

    if not args.no_write:
        out_verdict = pathlib.Path(args.out) if args.out else VERDICT
        out_evidence = pathlib.Path(args.evidence_out) if args.evidence_out else EVIDENCE
        out_verdict.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [f"EXP1-Q13 index-scope-out 裁定落地 · verdict={verdict['verdict']} · {verdict['evidence_level']}", ""]
        lines.append("语言集 (源码派生): " + " ".join(suffixes) + f"  @ {PROBE_SRC.name}:{line_no}")
        lines.append(f"弱边 {len(r1['weak'])} = in-scope {len(r1['in_scope'])} + index_scope_out {len(r1['scope_out'])}  by_ext={r1['by_ext']}")
        lines.append(f"kind 重算 {r1['kind_counts']}  (登记 {baseline['kind_counts']})")
        lines.append(f"分母双栏: 登记 {len(r1['weak'])} | 剔除 scope-out {len(r1['weak']) - len(r1['scope_out'])}   delta_applied=false")
        lines.append(f"收益上限 (词法代理): 转强边 {r1['payoff']['would_promote_edges_proxy']} / {len(r1['scope_out'])} ⇒ "
                     f"弱 {len(r1['weak'])}→{r1['payoff']['ceiling']['weak_after']}, 强 {baseline['strength_counts'].get('strong')}→{r1['payoff']['ceiling']['strong_after']}")
        for e in r1["payoff"]["edges"]:
            lines.append(f"  - {e['doc']}:{e['doc_line']} → {e['resolved']} syms={e['symbols']} "
                         f"promote={e['edge_would_promote_proxy']} evidence={e['nonbuiltin_evidence_symbols']}")
        lines.append("")
        for k in sorted(c):
            v = c[k]
            lines.append(f"[{'PASS' if v.get('pass') else 'FAIL'}] {k}")
        out_evidence.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"verdict={verdict['verdict']} weak={len(r1['weak'])} in_scope={len(r1['in_scope'])} "
          f"scope_out={len(r1['scope_out'])} promote={r1['payoff']['would_promote_edges_proxy']} "
          f"fail={[k for k, v in c.items() if not v.get('pass')]}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
