#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kpi_dcr.py —— DCR (Decision Compliance Rate) 判定脚本。

只依赖 Python 标准库。从**真实装配输出**计算:
  DCR = agree / N            agree = 实际 disposition == 期望 disposition
  覆盖率 = (Proceed + Violation) / N    分母含弃权与畸形 (两者单列报出)
  弃权率 = Abstained / N      畸形率 = Malformed / N
  每 category 的 N / 一致数 / 一致率
  混淆矩阵 (expected × actual)
  未一致条目明细 (id + 期望 + 实际 + reason)

可证伪性 (硬约束):
  * cases 里任一条缺 expected_disposition / expected_verdict / id ⇒ error + 非零退出
  * id 重复、decisions 缺条目、decisions 多出条目、disposition 取值越界 ⇒ error + 非零退出
  * **绝不静默跳过任何条目**

内核层对比 (--kernel):
  传入 `agent.rover check --json` 风格输出 (每行字段 verdict/counterexample/ms)。
  行内无 id 时按**行序**与 cases 对齐 (报告里显式声明该假设); 行数不等 ⇒ error。

用法:
  python3 scripts/kpi_dcr.py --cases eval/dcr/dcr_cases.jsonl \
                             --decisions <agent_out.jsonl> \
                             [--kernel <agent.rover_out.jsonl>] [--json]
退出码: 0 = 跑通; 2 = 输入/标签/对齐错误。
"""
import argparse
import json
import sys
from collections import Counter, OrderedDict

DISPOSITIONS = ("Proceed", "Violation", "Abstained", "Malformed")
VERDICTS = ("Proved", "Refuted", "Vacuous", "Unknown", "Malformed", "NoFormal")
CATEGORIES = ("entail", "refute", "vacuous", "out_of_fragment", "malformed", "absent")

# 内核 verdict → 装配层 disposition 的映射 (用于内核层对比)
VERDICT_TO_DISPO = {
    "Proved": "Proceed",
    "Refuted": "Violation",
    "Vacuous": "Violation",
    "Unknown": "Abstained",
    "Malformed": "Malformed",
    "NoFormal": "Proceed",
}


class InputError(Exception):
    pass


def _iter_jsonl(path, what):
    try:
        fh = open(path, "r", encoding="utf-8-sig")
    except OSError as e:
        raise InputError("cannot open %s file %r: %s" % (what, path, e))
    with fh as f:
        for lineno, raw in enumerate(f, 1):
            s = raw.strip()
            if not s:
                continue  # 空行允许(末尾换行), 但下面的行都必须可解
            try:
                yield lineno, json.loads(s)
            except json.JSONDecodeError as e:
                raise InputError("%s %r line %d: bad JSON: %s" % (what, path, lineno, e))


def load_cases(path):
    rows = []
    seen = set()
    for lineno, o in _iter_jsonl(path, "cases"):
        if not isinstance(o, dict):
            raise InputError("cases line %d: not a JSON object" % lineno)
        cid = o.get("id")
        if not isinstance(cid, str) or not cid:
            raise InputError("cases line %d: missing/blank 'id'" % lineno)
        if cid in seen:
            raise InputError("cases line %d: duplicate id %r" % (lineno, cid))
        seen.add(cid)
        cat = o.get("category")
        if cat not in CATEGORIES:
            raise InputError("cases %s: category %r not in %s" % (cid, cat, list(CATEGORIES)))
        ed = o.get("expected_disposition")
        if ed not in DISPOSITIONS:
            raise InputError(
                "cases %s: expected_disposition missing/invalid (%r); 标签缺失必须报错, 不得猜"
                % (cid, ed))
        ev = o.get("expected_verdict")
        if ev not in VERDICTS:
            raise InputError(
                "cases %s: expected_verdict missing/invalid (%r); 标签缺失必须报错" % (cid, ev))
        if "contract" not in o:
            raise InputError("cases %s: missing 'contract' field" % cid)
        rows.append(o)
    if not rows:
        raise InputError("cases %r: no rows" % path)
    return rows


def load_decisions(path, case_ids):
    by_id = OrderedDict()
    order = []
    for lineno, o in _iter_jsonl(path, "decisions"):
        if not isinstance(o, dict):
            raise InputError("decisions line %d: not a JSON object" % lineno)
        cid = o.get("id")
        if not isinstance(cid, str) or not cid:
            raise InputError("decisions line %d: missing/blank 'id'" % lineno)
        if cid in by_id:
            raise InputError("decisions line %d: duplicate id %r" % (lineno, cid))
        d = o.get("disposition")
        if d not in DISPOSITIONS:
            raise InputError("decisions %s: disposition missing/invalid (%r)" % (cid, d))
        v = o.get("verdict")
        if v not in VERDICTS:
            raise InputError("decisions %s: verdict missing/invalid (%r)" % (cid, v))
        by_id[cid] = o
        order.append(cid)

    missing = [c for c in case_ids if c not in by_id]
    extra = [c for c in order if c not in set(case_ids)]
    if missing or extra:
        raise InputError(
            "decisions/cases id mismatch: missing=%d %s extra=%d %s"
            % (len(missing), missing[:8], len(extra), extra[:8]))
    return by_id


def load_kernel(path, n_cases, case_ids):
    rows = []
    for lineno, o in _iter_jsonl(path, "kernel"):
        if not isinstance(o, dict):
            raise InputError("kernel line %d: not a JSON object" % lineno)
        if "verdict" not in o:
            raise InputError("kernel line %d: missing 'verdict'" % lineno)
        rows.append(o)
    has_id = all(isinstance(r.get("id"), str) and r["id"] for r in rows)
    if has_id:
        m = {r["id"]: r for r in rows}
        if set(m) != set(case_ids):
            raise InputError(
                "kernel ids mismatch with cases: missing=%s extra=%s"
                % (sorted(set(case_ids) - set(m))[:8], sorted(set(m) - set(case_ids))[:8]))
        return [m[c] for c in case_ids], "by_id"
    if len(rows) != n_cases:
        raise InputError(
            "kernel rows=%d != cases=%d and kernel rows carry no 'id' ⇒ 无法安全对齐 (不猜)"
            % (len(rows), n_cases))
    return rows, "by_row_order"


def pct(x, n):
    return (100.0 * x / n) if n else 0.0


def compute(cases, decisions, kernel=("", None)):
    n = len(cases)
    agree = 0
    per_cat = OrderedDict((c, {"n": 0, "agree": 0}) for c in CATEGORIES)
    conf = OrderedDict((e, Counter()) for e in DISPOSITIONS)
    mismatches = []
    dispo_count = Counter()
    unsafe = []          # 期望 != 实际 且 实际是**主动**裁决 (Proceed/Violation) ⇒ 危险
    decisive = 0         # 实际未弃权/未畸形的条目数
    decisive_agree = 0   # 在决断条目里与期望一致的条数

    for c in cases:
        cid = c["id"]
        exp = c["expected_disposition"]
        ev = c["expected_verdict"]
        d = decisions[cid]
        act = d["disposition"]
        av = d.get("verdict")
        per_cat[c["category"]]["n"] += 1
        conf[exp][act] += 1
        dispo_count[act] += 1
        if act in ("Proceed", "Violation"):
            decisive += 1
            if act == exp:
                decisive_agree += 1
        if act == exp:
            agree += 1
            per_cat[c["category"]]["agree"] += 1
        else:
            mismatches.append({
                "id": cid, "category": c["category"],
                "expected_disposition": exp, "expected_verdict": ev,
                "actual_disposition": act, "actual_verdict": av,
                "reason": d.get("reason"), "counterexample": d.get("counterexample"),
            })
            if act in ("Proceed", "Violation"):
                unsafe.append(cid)

    rep = OrderedDict()
    rep["n"] = n
    rep["dcr"] = agree / n if n else 0.0
    rep["agree"] = agree
    rep["coverage"] = dispo_count["Proceed"] + dispo_count["Violation"]
    rep["coverage_rate"] = rep["coverage"] / n if n else 0.0
    rep["abstained"] = dispo_count["Abstained"]
    rep["abstain_rate"] = rep["abstained"] / n if n else 0.0
    rep["malformed"] = dispo_count["Malformed"]
    rep["malformed_rate"] = rep["malformed"] / n if n else 0.0
    rep["proceed"] = dispo_count["Proceed"]
    rep["violation"] = dispo_count["Violation"]
    rep["decisive"] = decisive
    rep["decisive_accuracy"] = (decisive_agree / decisive) if decisive else 0.0
    rep["unsafe"] = unsafe
    rep["unsafe_count"] = len(unsafe)
    rep["per_category"] = OrderedDict(
        (k, {"n": v["n"], "agree": v["agree"], "rate": (v["agree"] / v["n"]) if v["n"] else 0.0})
        for k, v in per_cat.items())
    rep["confusion"] = OrderedDict((e, OrderedDict((a, conf[e][a]) for a in DISPOSITIONS))
                                   for e in DISPOSITIONS)
    rep["mismatches"] = mismatches

    kpath, korder, krow = kernel
    if kpath:
        k_exp = k_asm = 0
        k_percat = OrderedDict((c, {"n": 0, "exp": 0, "asm": 0}) for c in CATEGORIES)
        k_mism = []
        for c, k in zip(cases, krow):
            kv = k.get("verdict")
            if kv not in VERDICT_TO_DISPO:
                raise InputError("kernel %s: verdict %r unknown" % (c["id"], kv))
            kd = VERDICT_TO_DISPO[kv]
            ad = decisions[c["id"]]["disposition"]
            k_percat[c["category"]]["n"] += 1
            if kd == c["expected_disposition"]:
                k_exp += 1
                k_percat[c["category"]]["exp"] += 1
            if kd == ad:
                k_asm += 1
                k_percat[c["category"]]["asm"] += 1
            if kd != ad:
                k_mism.append({"id": c["id"], "kernel_verdict": kv,
                               "kernel_disposition": kd, "assembly_disposition": ad})
        rep["kernel"] = OrderedDict([
            ("path", kpath), ("alignment", korder),
            ("kernel_vs_expected_agree", k_exp),
            ("kernel_vs_expected_rate", k_exp / n if n else 0.0),
            ("kernel_vs_assembly_agree", k_asm),
            ("kernel_vs_assembly_rate", k_asm / n if n else 0.0),
            ("per_category", k_percat),
            ("kernel_vs_assembly_mismatches", k_mism),
        ])
    return rep


def render(rep):
    L = []
    n = rep["n"]
    L.append("=" * 78)
    L.append("DCR 判定报告  (DCR = agree/N, agree = actual disposition == expected)")
    L.append("=" * 78)
    L.append("N (总条目)              = %d" % n)
    L.append("DCR                     = %d/%d = %.4f  (%.2f%%)"
             % (rep["agree"], n, rep["dcr"], 100 * rep["dcr"]))
    L.append("覆盖率 (Proceed+Violation) = %d/%d = %.4f  (%.2f%%)"
             % (rep["coverage"], n, rep["coverage_rate"], 100 * rep["coverage_rate"]))
    L.append("  其中 Proceed          = %d (%.2f%%)" % (rep["proceed"], pct(rep["proceed"], n)))
    L.append("  其中 Violation        = %d (%.2f%%)" % (rep["violation"], pct(rep["violation"], n)))
    L.append("弃权率 (Abstained)      = %d/%d = %.2f%%" % (rep["abstained"], n, 100 * rep["abstain_rate"]))
    L.append("畸形率 (Malformed)      = %d/%d = %.2f%%" % (rep["malformed"], n, 100 * rep["malformed_rate"]))
    L.append("决断条目 (未弃权/未畸形) = %d" % rep["decisive"])
    L.append("决断条目一致率           = %.4f  (%.2f%%)"
             % (rep["decisive_accuracy"], 100 * rep["decisive_accuracy"]))
    L.append("主动误判 (unsafe: 期望≠实际 且 实际 Proceed/Violation) = %d %s"
             % (rep["unsafe_count"], rep["unsafe"][:10] if rep["unsafe"] else ""))
    L.append("-" * 78)
    L.append("%-16s %5s %7s %10s" % ("category", "N", "agree", "rate"))
    for k, v in rep["per_category"].items():
        L.append("%-16s %5d %7d %9.2f%%" % (k, v["n"], v["agree"], 100 * v["rate"]))
    L.append("-" * 78)
    L.append("混淆矩阵 (行=expected, 列=actual):")
    L.append("%-12s %10s %10s %10s %10s" % ("", *DISPOSITIONS))
    for e in DISPOSITIONS:
        row = rep["confusion"][e]
        L.append("%-12s %10d %10d %10d %10d" % (e, row["Proceed"], row["Violation"],
                                                row["Abstained"], row["Malformed"]))
    L.append("-" * 78)
    L.append("未一致条目明细 (id / category / 期望 / 实际 / reason): %d 条" % len(rep["mismatches"]))
    if not rep["mismatches"]:
        L.append("  (无)")
    for m in rep["mismatches"]:
        L.append("  %-6s %-16s exp=%-10s(%s) act=%-10s(%s) reason=%s"
                 % (m["id"], m["category"], m["expected_disposition"], m["expected_verdict"],
                    m["actual_disposition"], m["actual_verdict"], m["reason"]))
    if "kernel" in rep:
        k = rep["kernel"]
        L.append("-" * 78)
        L.append("内核层对比 (--kernel)")
        L.append("  kernel file          = %s" % k["path"])
        L.append("  对齐假设              = %s" % (
            "行内带 id, 按 id 对齐" if k["alignment"] == "by_id"
            else "行内无 id ⇒ **按行序与 cases 对齐** (该假设未由数据本身保证)"))
        L.append("  内核 verdict→disposition 映射 (与闸门同表)")
        L.append("  内核层 vs 期望一致率   = %d/%d = %.2f%%"
                 % (k["kernel_vs_expected_agree"], n, 100 * k["kernel_vs_expected_rate"]))
        L.append("  内核层 vs 装配层一致率 = %d/%d = %.2f%%"
                 % (k["kernel_vs_assembly_agree"], n, 100 * k["kernel_vs_assembly_rate"]))
        L.append("  %-16s %5s %10s %10s" % ("category", "N", "kernel≈exp", "kernel≈asm"))
        for kk, v in k["per_category"].items():
            L.append("  %-16s %5d %10d %10d" % (kk, v["n"], v["exp"], v["asm"]))
        if k["kernel_vs_assembly_mismatches"]:
            L.append("  内核层 ≠ 装配层 明细: %d 条" % len(k["kernel_vs_assembly_mismatches"]))
            for m in k["kernel_vs_assembly_mismatches"][:40]:
                L.append("    %-6s kernel=%-10s(%-10s) assembly=%s"
                         % (m["id"], m["kernel_verdict"], m["kernel_disposition"],
                            m["assembly_disposition"]))
            dispo_seen = {}
            for m in k["kernel_vs_assembly_mismatches"]:
                dispo_seen.setdefault(m["assembly_disposition"], []).append(m["id"])
            L.append("  说明: 上述差异 **不是** 内核判定错误, 而是层职责不同:")
            if "Proceed" in dispo_seen:
                L.append("    - contract 为 null/空/纯自然语言 (absent): 原始内核 CLI 无契约层的 "
                         "no_formal 语义, 空输入返回 Malformed, 而闸门按 NoFormal→Proceed 处置")
            if "Malformed" in dispo_seen:
                L.append("    - 仅 goal 无 premise 等: 契约层要求 premise/no_formal, 原始内核 CLI "
                         "允许 goal-only, 故 CLI 能 Refute 而闸门判 Malformed")
            L.append("    ⇒ 内核层对比的期望列应读作“原始内核能力”, 装配层才是契约语义的裁决")
        else:
            L.append("  内核层与装配层处置完全一致")
    L.append("=" * 78)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="DCR 判定脚本 (stdlib only)")
    ap.add_argument("--cases", required=True, help="判定题集 jsonl")
    ap.add_argument("--decisions", required=True, help="真实装配输出 jsonl")
    ap.add_argument("--kernel", default=None, help="agent.rover check --json 风格输出 (可选)")
    ap.add_argument("--json", action="store_true", help="额外打印机器可读 JSON")
    a = ap.parse_args(argv)

    try:
        cases = load_cases(a.cases)
        case_ids = [c["id"] for c in cases]
        decisions = load_decisions(a.decisions, case_ids)
        kernel = (None, None, None)
        if a.kernel:
            krows, kalign = load_kernel(a.kernel, len(cases), case_ids)
            kernel = (a.kernel, kalign, krows)
        rep = compute(cases, decisions, kernel)
    except InputError as e:
        sys.stderr.write("ERROR: %s\n" % e)
        return 2

    print(render(rep))
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
