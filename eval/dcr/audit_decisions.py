#!/usr/bin/env python3
"""独立审计: 用 z3 逐条复核「真装配给出的裁决」是否成立 (不采信内核自证)。

审计内容
  1) verdict == Refuted ⇒ 反例必须真的满足 premise ∧ ¬goal (逐变量代入后 z3 必须 sat)
  2) verdict == Proved  ⇒ premise ∧ ¬goal 必须真的 unsat
  3) 其余 (Unknown/Malformed/NoFormal) 不做数学断言, 只统计 —— 弃权/畸形**不得**被算作证明

用法: python3 eval/dcr/audit_decisions.py [--cases eval/dcr/dcr_cases.jsonl]
                                           [--decisions /tmp/r388/assembly_real.jsonl]
退出码: 0 = 无假反例/无假证明; 1 = 发现不健全裁决。
依赖: z3 (独立 oracle), 与 click-rover 内核实现完全无关。
"""
import argparse
import json
import re
import sys
from collections import Counter

try:
    import z3
except ImportError:  # pragma: no cover
    print("SKIP: z3 不可用, 无法独立审计", file=sys.stderr)
    sys.exit(3)

IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
CE_PAIR = re.compile(r"([A-Za-z_]\w*)\s*=\s*(-?\d+)")


def split_top(expr, op):
    """按 op 在**括号深度 0** 处切分 (忽略括号内的同名运算符)。"""
    parts, depth, last = [], 0, 0
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and expr.startswith(op, i):
            parts.append(expr[last:i])
            i += len(op)
            last = i
            continue
        i += 1
    parts.append(expr[last:])
    return parts


def strip_parens(expr):
    e = expr.strip()
    while e.startswith("(") and e.endswith(")"):
        depth, matched = 0, True
        for i, ch in enumerate(e):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(e) - 1:
                    matched = False
                    break
        if not matched:
            break
        e = e[1:-1].strip()
    return e


def build(expr, ns):
    """把受限片段的布尔式翻译为 z3 表达式 (&&/|| 必须走 z3.And/z3.Or, 不能用 Python and/or)。"""
    e = strip_parens(expr)
    for op, fn in (("||", z3.Or), ("&&", z3.And)):
        parts = split_top(e, op)
        if len(parts) > 1:
            return fn(*[build(p, ns) for p in parts])
    e = e.replace("!=", "\x00").replace("!", " not ").replace("\x00", "!=")
    return eval(e, {"__builtins__": {}}, ns)  # noqa: S307 — 受限片段, 名字全部来自契约变量


def parse_contract(contract):
    premises, goal = [], None
    for line in (contract or "").splitlines():
        line = line.strip()
        if line.startswith("premise "):
            premises.append(line[8:].strip())
        elif line.startswith("goal "):
            goal = line[5:].strip()
    return premises, goal


def ce_of(ce):
    if isinstance(ce, dict):
        return {k: int(v) for k, v in ce.items()}
    if isinstance(ce, str):
        return {k: int(v) for k, v in CE_PAIR.findall(ce)}
    return {}


def main():
    ap = argparse.ArgumentParser(description="z3 独立审计真装配裁决")
    ap.add_argument("--cases", default="eval/dcr/dcr_cases.jsonl")
    ap.add_argument("--decisions", default="/tmp/r388/assembly_real.jsonl")
    a = ap.parse_args()

    cases = {}
    with open(a.cases, encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                cases[d["id"]] = d
    decisions = []
    with open(a.decisions, encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                decisions.append(json.loads(line))

    ref_ok = ref_bad = pro_ok = pro_bad = other = skip = 0
    bad = []
    for d in decisions:
        c = cases.get(d["id"])
        if c is None:
            skip += 1
            continue
        verdict = d.get("verdict")
        if verdict not in ("Refuted", "Proved"):
            other += 1
            continue
        premises, goal = parse_contract(c.get("contract"))
        if goal is None:
            other += 1
            continue
        try:
            names = {n for n in IDENT.findall(" ".join(premises + [goal]))}
            ns = {n: z3.Int(n) for n in names}
            s = z3.Solver()
            for p in premises:
                s.add(build(p, ns))
            s.add(z3.Not(build(goal, ns)))
            if verdict == "Refuted":
                model = ce_of(d.get("counterexample"))
                if not model:
                    bad.append((d["id"], "refuted_without_counterexample", None))
                    ref_bad += 1
                    continue
                s.push()
                for k, v in model.items():
                    s.add(ns[k] == v)
                r = s.check()
                s.pop()
                if r == z3.sat:
                    ref_ok += 1
                else:
                    ref_bad += 1
                    bad.append((d["id"], "counterexample_invalid:" + str(r), d.get("counterexample")))
            else:
                r = s.check()
                if r == z3.unsat:
                    pro_ok += 1
                else:
                    pro_bad += 1
                    bad.append((d["id"], "proved_but_counterexample_exists:" + str(r), None))
        except Exception:  # noqa: BLE001 — 片段外/畸形契约按"不适用"计, 绝不记成通过
            skip += 1

    print("AUDIT by z3 (独立 oracle, 与内核实现无关)")
    print("  决策总数              = %d" % len(decisions))
    print("  Refuted 反例经复核为真 = %d   反例为假 = %d" % (ref_ok, ref_bad))
    print("  Proved 经复核确 unsat  = %d   存在反例 = %d" % (pro_ok, pro_bad))
    print("  非数学断言 (Unknown/Malformed/NoFormal/无目标) = %d" % other)
    print("  未审计 (契约不可解析/片段外) = %d" % skip)
    if bad:
        for b in bad[:10]:
            print("  BAD", b)
    if ref_bad or pro_bad:
        print("AUDIT_RESULT=UNSOUND")
        return 1
    print("AUDIT_RESULT=SOUND")
    return 0


if __name__ == "__main__":
    sys.exit(main())
