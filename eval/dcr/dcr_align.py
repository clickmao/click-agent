#!/usr/bin/env python3
"""DCR 单一口径重算 (FAVA 语义) — eval/dcr/dcr_align.py

背景
----
本仓原有 DCR 报表按 **四类处置一致率** 计算 (实际处置 == 期望处置, N=145) ⇒ 恒为 100%,
与 FAVA 正文口径 (`DCR = (TP+TN)/(TP+TN+FP+FN)`, **无弃权项**, 不确定一律 fail-closed 记 block)
不是同一个量。两者数值不可直接比较, 也不能并列汇报 (双口径)。

本脚本按 FAVA 单一（二元）口径重算, 并给出:
  * 二元混淆矩阵 (TP/TN/FP/FN) + DCR
  * 逐 category 二元分解
  * **口径敏感度表** (弃权/畸形如何折算 → DCR 摆动多少) —— 用于回答「这个数字稳不稳」
  * 独立实现交叉对账 (与 C# 侧 eval/dcr/dcr_report.txt 的两个数对账)

口径映射 (显式, 可审计)
------------------------
期望侧 (cases.expected_disposition):
  Proceed                -> allow      (闸门放行)
  其余 (Violation/Abstained/Malformed) -> block
实际侧 (assembly_out.disposition):
  Proceed                -> allow
  其余 (Violation/Abstained/Malformed) -> block   # fail-closed: 弃权/畸形都算阻断

用法
----
  python3 eval/dcr/dcr_align.py                 # 重算 + 落 docs/reports/dcr/dcr-single-metric.json
  python3 eval/dcr/dcr_align.py --selftest      # 负控 (含解析 oracle, 不读真实数据)
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "dcr_cases.jsonl")
ASSEMBLY = os.path.join(HERE, "assembly_out.jsonl")
CSHARP_REPORT = os.path.join(HERE, "dcr_report.txt")
OUT_JSON = os.path.join(HERE, "..", "..", "docs", "reports", "dcr", "dcr-single-metric.json")

ALLOW = "allow"
BLOCK = "block"
PROCEED = "Proceed"


def expected_binary(case: dict) -> str:
    """期望侧二元化: 只有 Proceed 才是 allow (缺失≠错误已在 cases 里落成 Proceed)。"""
    return ALLOW if case["expected_disposition"] == PROCEED else BLOCK


def actual_binary(decision: dict) -> str:
    """实际侧二元化: fail-closed — 不是 Proceed 一律算 block (含 Abstained/Malformed)。"""
    return ALLOW if decision["disposition"] == PROCEED else BLOCK


def confusion(pairs):
    """pairs: iterable of (expected, actual) 二元值 -> (tp, tn, fp, fn)。"""
    tp = tn = fp = fn = 0
    for exp, act in pairs:
        if exp == BLOCK and act == BLOCK:
            tp += 1
        elif exp == ALLOW and act == ALLOW:
            tn += 1
        elif exp == ALLOW and act == BLOCK:
            fp += 1
        elif exp == BLOCK and act == ALLOW:
            fn += 1
        else:  # pragma: no cover - 防御
            raise ValueError("bad pair %r/%r" % (exp, act))
    return tp, tn, fp, fn


def dcr_of(tp, tn, fp, fn):
    n = tp + tn + fp + fn
    return (tp + tn) / n if n else float("nan")


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_pairs():
    cases = load_jsonl(CASES)
    decs = load_jsonl(ASSEMBLY)
    by_id = {}
    for d in decs:
        if d["id"] in by_id:
            raise SystemExit("重复 id in assembly_out: %s" % d["id"])
        by_id[d["id"]] = d
    ids_cases = [c["id"] for c in cases]
    if len(set(ids_cases)) != len(ids_cases):
        raise SystemExit("cases 有重复 id")
    missing = [i for i in ids_cases if i not in by_id]
    extra = [i for i in by_id if i not in set(ids_cases)]
    if missing or extra:
        raise SystemExit("按 id 对账失败 missing=%s extra=%s" % (missing[:5], extra[:5]))
    return [(c, by_id[c["id"]]) for c in cases]


def read_csharp_numbers(path=CSHARP_REPORT):
    """从 C# 侧报表抽可对账数 (独立实现交叉对账用)。

    只抽 C# 侧**独立产生**的计数, 不抽任何由本脚本口径推导的量。
    """
    got = {}
    if not os.path.exists(path):
        return got
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith("N (总条目)"):
                got["N"] = int(line.split("=")[1].strip())
            elif line.startswith("覆盖率"):
                frag = line.split("=")[1].strip()
                got["decidable"] = int(frag.split("/")[0].strip())
            elif line.startswith("  其中 Proceed"):
                got["proceed"] = int(line.split("=")[1].strip().split()[0])
            elif line.startswith("  其中 Violation"):
                got["violation"] = int(line.split("=")[1].strip().split()[0])
            elif line.startswith("弃权率"):
                frag = line.split("=")[1].strip()
                got["abstained"] = int(frag.split("/")[0].strip())
            elif line.startswith("畸形率"):
                frag = line.split("=")[1].strip()
                got["malformed"] = int(frag.split("/")[0].strip())
    return got


def selftest() -> int:
    """负控: 全部断言必须能 FAIL (否则巡检/判定是空心的)。不读真实数据。"""
    from collections import Counter

    ok = 0
    fails = []

    def check(name, cond):
        nonlocal ok
        if cond:
            ok += 1
            print("OK   " + name)
        else:
            fails.append(name)
            print("FAIL " + name)

    # ① 合成小样本: 3 block 期望 + 2 allow 期望, 实际: 2 对 1 错(FP) / 1 对 1 错(FN)
    synth = [
        (BLOCK, BLOCK), (BLOCK, BLOCK), (BLOCK, ALLOW),   # tp,tp,fn
        (ALLOW, ALLOW), (ALLOW, BLOCK),                    # tn,fp
    ]
    tp, tn, fp, fn = confusion(synth)
    check("混淆矩阵计数正确 (tp=2,tn=1,fp=1,fn=1)", (tp, tn, fp, fn) == (2, 1, 1, 1))
    check("DCR=3/5=0.6", abs(dcr_of(tp, tn, fp, fn) - 0.6) < 1e-12)

    # ② 解析 oracle: 随机独立二元标签的期望一致率 = (P*P + B*B)/N^2
    n_allow, n_block = 51, 94
    pairs_real = [(ALLOW, None)]
    rng = random.Random(20260913)
    N = 145
    exp_side = [ALLOW] * n_allow + [BLOCK] * n_block
    analytic = (n_allow * n_allow + n_block * n_block) / (N * N)
    rng.shuffle(exp_side)
    tot = 0.0
    reps = 400
    for _ in range(reps):
        act = [ALLOW] * n_allow + [BLOCK] * n_block
        rng.shuffle(act)
        t2, n2, f2, m2 = confusion(zip(exp_side, act))
        tot += dcr_of(t2, n2, f2, m2)
    mean_shuffled = tot / reps
    check("洗牌负控均值 ≈ 解析值 %.4f (±0.05)" % analytic, abs(mean_shuffled - analytic) < 0.05)

    # ③ 单点翻转 ⇒ 恰好 -1/N (FP=FN=0 时)
    pairs = list(zip(exp_side, exp_side))
    base = dcr_of(*confusion(pairs))
    flipped = pairs[:-1] + [(pairs[-1][0], ALLOW if pairs[-1][1] == BLOCK else BLOCK)]
    delta = base - dcr_of(*confusion(flipped))
    check("单点翻转 Δ == 1/145", abs(delta - 1.0 / 145) < 1e-12)

    # ④ 全 allow / 全 block 的解析下限 (防「常量分类器也能高分」误读)
    all_allow = [(ALLOW, ALLOW)] * n_allow + [(BLOCK, ALLOW)] * n_block
    all_block = [(ALLOW, BLOCK)] * n_allow + [(BLOCK, BLOCK)] * n_block
    check("全 allow ⇒ DCR=51/145=0.3517",
          abs(dcr_of(*confusion(all_allow)) - n_allow / N) < 1e-12)
    check("全 block ⇒ DCR=94/145=0.6483",
          abs(dcr_of(*confusion(all_block)) - n_block / N) < 1e-12)

    # ⑤ 口径敏感度必须是真敏感: abstain→allow 折算会改变 DCR
    check("弃权折算方向正确 (abstain→allow 降 DCR)",
          dcr_of(*confusion([(BLOCK, ALLOW)] * 39 + [(BLOCK, BLOCK)] * 55 + [(ALLOW, ALLOW)] * 51)) < 1.0)

    total = ok + len(fails)
    print("selftest %d/%d" % (ok, total))
    return 0 if not fails else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    pairs_raw = load_pairs()
    pairs = [(expected_binary(c), actual_binary(d)) for c, d in pairs_raw]
    tp, tn, fp, fn = confusion(pairs)
    dcr = dcr_of(tp, tn, fp, fn)
    n = len(pairs)

    # 逐 category 二元分解
    per_cat = {}
    for c, d in pairs_raw:
        cat = c["category"]
        slot = per_cat.setdefault(cat, {"N": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0,
                                        "expected": set(), "actual": set()})
        e, a = expected_binary(c), actual_binary(d)
        t2, n2, f2, m2 = confusion([(e, a)])
        slot["N"] += 1
        slot["tp"] += t2
        slot["tn"] += n2
        slot["fp"] += f2
        slot["fn"] += m2
        slot["expected"].add(c["expected_disposition"])
        slot["actual"].add(d["disposition"])
    for v in per_cat.values():
        v["dcr"] = round(dcr_of(v["tp"], v["tn"], v["fp"], v["fn"]), 6)
        v["expected"] = sorted(v["expected"])
        v["actual"] = sorted(v["actual"])

    # 口径敏感度: 同一数据在不同弃权/畸形折算下的 DCR
    raw_exp = [expected_binary(c) for c, _ in pairs_raw]
    raw_act = [d["disposition"] for _, d in pairs_raw]
    sens = {}
    sens["fail-closed (本口径: 非 Proceed 一律 block)"] = {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "DCR": round(dcr, 6), "N": n}
    alt = [(e, ALLOW if a == PROCEED else (BLOCK if e == BLOCK else ALLOW)) for e, a in zip(raw_exp, raw_act)]
    # permissive: 只有 Violation 算 block, 弃权/畸形按放行
    perm = [(e, BLOCK if a == "Violation" else ALLOW) for e, a in zip(raw_exp, raw_act)]
    t2, n2, f2, m2 = confusion(perm)
    sens["弃权/畸形按放行 (Violation 才算 block)"] = {
        "tp": t2, "tn": n2, "fp": f2, "fn": m2, "DCR": round(dcr_of(t2, n2, f2, m2), 6), "N": n}
    # 排除弃权+畸形: 只在可决断集上算 (等价于只保留 entail/refute/absent)
    dec = [(e, ALLOW if a == PROCEED else BLOCK) for e, a in zip(raw_exp, raw_act)
           if a in (PROCEED, "Violation")]
    t3, n3, f3, m3 = confusion(dec)
    sens["仅可决断集 (排除弃权/畸形)"] = {
        "tp": t3, "tn": n3, "fp": f3, "fn": m3, "DCR": round(dcr_of(t3, n3, f3, m3), 6), "N": len(dec)}
    # 四类处置一致率 (旧口径, 仅作对照)
    agree4 = sum(1 for c, d in pairs_raw if c["expected_disposition"] == d["disposition"])
    sens["旧口径: 四类处置一致率 (对照, 非本指标)"] = {
        "agree": agree4, "N": n, "rate": round(agree4 / n, 6)}

    spread = [v["DCR"] for v in sens.values() if "DCR" in v]
    spread_pp = (max(spread) - min(spread)) * 100

    cs = read_csharp_numbers()
    n_actual_violation = sum(1 for _, d in pairs_raw if d["disposition"] == "Violation")
    n_actual_proceed = sum(1 for _, d in pairs_raw if d["disposition"] == PROCEED)
    # C# 侧 (装配层) 独立计数的三条恒等式 —— 任一条破即两实现不一致
    xchecks = {
        "N 一致": cs.get("N") == n,
        "Proceed 计数一致 (= TN 侧)": cs.get("proceed") == n_actual_proceed == tn,
        "可决断集一致 (= Proceed+Violation)": cs.get("decidable") == cs.get("proceed", 0) + cs.get("violation", 0),
        "弃权+畸形 = N-可决断": cs.get("abstained", 0) + cs.get("malformed", 0) == n - cs.get("decidable", 0),
    }
    label_src = {}
    for c, _ in pairs_raw:
        label_src[c.get("label_source", "?")] = label_src.get(c.get("label_source", "?"), 0) + 1

    out = {
        "metric": "DCR",
        "spec": "DCR = (TP+TN)/(TP+TN+FP+FN); 无弃权项; 非 Proceed(fail-closed) 记 block",
        "spec_source": "FAVA 正文取证 docs/reports/dcr/dcr-align-fava-source-2026-09-13.md",
        "N": n,
        "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
        "DCR": round(dcr, 6),
        "per_category": per_cat,
        "sensitivity": sens,
        "sensitivity_spread_pp": round(spread_pp, 2),
        "cross_impl_csharp": {"raw": cs, "identities": xchecks,
                              "all_pass": all(xchecks.values())},
        "label_source": label_src,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)

    print("N=%d  TP=%d TN=%d FP=%d FN=%d  DCR=%.4f" % (n, tp, tn, fp, fn, dcr))
    print("口径敏感度跨度 = %.2f pp" % spread_pp)
    print("C# 独立实现交叉对账 %d/%d" % (sum(1 for v in xchecks.values() if v), len(xchecks)))
    for k, v in xchecks.items():
        print("   %s %s" % ("OK  " if v else "FAIL", k))
    for cat in sorted(per_cat):
        v = per_cat[cat]
        print("  %-16s N=%3d dcr=%.4f exp=%s act=%s" % (
            cat, v["N"], v["dcr"], ",".join(v["expected"]), ",".join(v["actual"])))
    print("→ " + os.path.relpath(OUT_JSON, os.path.join(HERE, "..", "..")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
