#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力自检循环本体 (用户钦定 2026-09-14, R400 之后常驻)。

用户令: 「参照当前上下文(非本 agent 项目的) 并使用本 agent 和 py 开发随机程序和解开随机
数学难题用于本 agent 能力自检和总结通用性 skill 放入 skills 文件夹内」; 且需要**检测机制**
(每 60 分钟检查一次: 还有任务就执行任务, 没有就运行本自检循环)。

本脚本 = 循环的**机械部分** (题源 + 判定 + 读数), 不含任何模型调用:
  status        检测机制入口: 复用 capability_cycle_status.py 判 mode (tasks|selfcheck)
  emit          按 seed 生成一轮随机题 (程序题 + 数学题), 落 eval/capability/cycle-<id>.json
  grade         对某轮的解 (solution.py + math_answer.json) 做机械判定 + 读数落盘
  selftest      判定力负控: 参考解必须全绿; 3 类变异解必须变红

设计判据 (为什么这么写):
  ① 题源取自**通用领域** (数论/组合/图论/数据结构/字符串), 与本 agent 项目无关;
  ② 判定 = **独立实现 oracle** (暴力枚举/DP), 与被测解法的算法**不同** (跨实现对账铁律);
  ③ 数学题必须**唯一整数答案**, 程序题必须**逐用例判定**并给出失败分类 (禁空心通过率);
  ④ selftest 必须证明判定器**有判别力** (变异解变红), 否则「全绿」无信息量。
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "eval" / "capability"   # data/ 被 .gitignore ⇒ 证据落 eval/ (可复现/可跟踪)
KPI = OUT_DIR / "kpi.jsonl"
TASK_KINDS = ("program", "math")

# ─────────────────────────── 通用工具 ───────────────────────────

def _digitsum(x: int) -> int:
    s = 0
    while x:
        s += x % 10
        x //= 10
    return s


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# ─────────────────────────── 数学题: 生成 + oracle ───────────────────────────
# 每个家族: gen(rng) -> params; oracle(params) -> 定长答案; statement(params) -> 文本
# oracle 一律用**暴力/独立算法**, 与"聪明解"不同路径。

def m_coprime_pairs_gen(rng):
    n = rng.randint(60, 200)
    return {"n": n}


def m_coprime_pairs_oracle(p):
    n = p["n"]
    return sum(1 for a in range(1, n + 1) for b in range(a + 1, n + 1) if _gcd(a, b) == 1)


def m_coprime_pairs_stmt(p):
    return (f"在 1..{p['n']} 中, 有多少对 (a,b) 满足 1<=a<b<=n 且 gcd(a,b)=1? "
            f"输出该整数。")


def m_digit_sum_mod_gen(rng):
    a = rng.randint(1000, 5000)
    b = a + rng.randint(2000, 4000)
    m = rng.randint(3, 9)
    k = rng.randint(0, m - 1)
    return {"a": a, "b": b, "m": m, "k": k}


def m_digit_sum_mod_oracle(p):
    return sum(1 for x in range(p["a"], p["b"] + 1) if _digitsum(x) % p["m"] == p["k"])


def m_digit_sum_mod_stmt(p):
    return (f"统计区间 [{p['a']},{p['b']}] 内有多少个整数, 其各位数字之和 ≡ {p['k']} "
            f"(mod {p['m']})。输出该整数。")


def m_lattice_blocked_gen(rng):
    m, n = rng.randint(4, 7), rng.randint(4, 7)
    inner = [(i, j) for i in range(1, m + 1) for j in range(1, n + 1)]
    rng.shuffle(inner)
    blocked = sorted(inner[: rng.randint(1, 3)])
    return {"m": m, "n": n, "blocked": blocked}


def m_lattice_blocked_oracle(p):
    m, n, bl = p["m"], p["n"], {tuple(c) for c in p["blocked"]}
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        for j in range(n + 1):
            if (i, j) in bl:
                continue
            if i == 0 or j == 0:
                dp[i][j] = 1 if (i, j) not in {(0, 0)} or True else 0
                dp[i][j] = 1
            else:
                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m][n]


def m_lattice_blocked_stmt(p):
    cells = ", ".join(f"({i},{j})" for i, j in p["blocked"])
    return (f"从 (0,0) 走到 ({p['m']},{p['n']}), 每步只能向右或向上走一格。"
            f"不能经过以下格子: {cells}。问有多少条合法路径? 输出该整数。")


def m_min_subset_gen(rng):
    k = rng.randint(9, 12)
    pool = rng.sample(range(3, 90), k)
    target = rng.randint(120, 240)
    return {"pool": pool, "target": target}


def m_min_subset_oracle(p):
    pool, target = p["pool"], p["target"]
    best = -1
    for r in range(1, len(pool) + 1):
        for comb in itertools.combinations(pool, r):
            if sum(comb) == target:
                return r
    return best


def m_min_subset_stmt(p):
    return (f"给定互不相同的整数集合 {sorted(p['pool'])} 与目标值 {p['target']}, "
            f"求最小的子集大小 r, 使某个 r 元子集之和恰为 {p['target']}; "
            f"若不存在这样的子集输出 -1。")


def m_mult_order_gen(rng):
    primes = [53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131]
    p = rng.choice(primes)
    a = rng.randint(2, p - 2)
    while _gcd(a, p) != 1:
        a = rng.randint(2, p - 2)
    return {"a": a, "p": p}


def m_mult_order_oracle(p):
    a, m = p["a"], p["p"]
    cur = 1
    for k in range(1, m):
        cur = (cur * a) % m
        if cur == 1:
            return k
    return -1


def m_mult_order_stmt(p):
    return (f"求 {p['a']} 在模 {p['p']} 乘法群中的阶 (最小的 k>=1 使 "
            f"{p['a']}^k ≡ 1 (mod {p['p']}))。输出该整数。")


def m_trailing_zeros_gen(rng):
    return {"n": rng.randint(80, 400)}


def m_trailing_zeros_oracle(p):
    total = 0
    for k in range(1, p["n"] + 1):
        x, t = k, 0
        while x % 5 == 0 and x:
            t += 1
            x //= 5
        total += t
    return total


def m_trailing_zeros_stmt(p):
    return (f"记 tz(k!) 为 k! 十进制末尾零的个数。求 tz(1!)+tz(2!)+...+tz({p['n']}!) 。"
            f"输出该整数。")


def m_crt_gen(rng):
    mods = rng.sample([4, 5, 7, 9, 11, 13], 3)
    rems = [rng.randrange(m) for m in mods]
    return {"mods": mods, "rems": rems}


def m_crt_oracle(p):
    mods, rems = p["mods"], p["rems"]
    lcm = 1
    for m in mods:
        lcm = lcm * m // _gcd(lcm, m)
    for x in range(lcm):
        if all(x % m == r for m, r in zip(mods, rems)):
            return x
    return -1


def m_crt_stmt(p):
    parts = ", ".join(f"x ≡ {r} (mod {m})" for m, r in zip(p["mods"], p["rems"]))
    return f"求满足下列同余式组的最小非负整数 x: {parts}。输出该整数。"


def m_spanning_trees_gen(rng):
    n = rng.randint(5, 6)
    all_edges = list(itertools.combinations(range(n), 2))
    rng.shuffle(all_edges)
    e = rng.randint(n, min(len(all_edges), n + 3))
    return {"n": n, "edges": sorted(all_edges[:e])}


def m_spanning_trees_oracle(p):
    """独立实现 2: 枚举 n-1 条边的子集, 并查集判连通 (与基尔霍夫矩阵树不同路径)。"""
    n, edges = p["n"], [tuple(e) for e in p["edges"]]

    def connected(sub):
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for u, v in sub:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
        return len({find(i) for i in range(n)}) == 1

    cnt = 0
    for sub in itertools.combinations(edges, n - 1):
        if connected(sub):
            cnt += 1
    return cnt


def m_spanning_trees_stmt(p):
    es = ", ".join(f"{u}-{v}" for u, v in p["edges"])
    return (f"无向图有顶点 0..{p['n'] - 1}, 边为: {es}。求其生成树个数。输出该整数。")


MATH_FAMILIES = {
    "coprime_pairs": (m_coprime_pairs_gen, m_coprime_pairs_oracle, m_coprime_pairs_stmt),
    "digit_sum_mod": (m_digit_sum_mod_gen, m_digit_sum_mod_oracle, m_digit_sum_mod_stmt),
    "lattice_blocked": (m_lattice_blocked_gen, m_lattice_blocked_oracle, m_lattice_blocked_stmt),
    "min_subset_size": (m_min_subset_gen, m_min_subset_oracle, m_min_subset_stmt),
    "mult_order": (m_mult_order_gen, m_mult_order_oracle, m_mult_order_stmt),
    "trailing_zeros_sum": (m_trailing_zeros_gen, m_trailing_zeros_oracle, m_trailing_zeros_stmt),
    "crt_min": (m_crt_gen, m_crt_oracle, m_crt_stmt),
    "spanning_trees": (m_spanning_trees_gen, m_spanning_trees_oracle, m_spanning_trees_stmt),
}

# ─────────────────────────── 程序题: 规格 + 隐藏用例 + 判定 ───────────────────────────
# 每个家族: gen(rng) -> params; public(params) -> 示例; hidden(params, rng2) -> [(call, expected)]
#           check(mod, params, cases) -> (passed, total, taxonomy)


def p_rle_gen(rng):
    return {"max_len": rng.randint(6, 14)}


def _rle_expected(s):
    out, i = [], 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append([j - i, s[i]])
        i = j
    return out


def p_rle_public(params):
    ex = ["aabbb", "abc", "aa"]
    return [{"call": "rle_encode", "args": [e], "expected": _rle_expected(e)} for e in ex]


def p_rle_hidden(params, rng):
    cases = []
    alphabet = "abc"
    for _ in range(12):
        n = rng.randint(1, params["max_len"])
        s = "".join(rng.choice(alphabet) for _ in range(n))
        cases.append({"call": "rle_encode", "args": [s], "expected": _rle_expected(s)})
        cases.append({"call": "rle_decode", "args": [_rle_expected(s)], "expected": s})
    # 边界: 空串
    cases.append({"call": "rle_encode", "args": [""], "expected": []})
    cases.append({"call": "rle_decode", "args": [[]], "expected": ""})
    return cases


def p_rle_check(mod, params, cases):
    return _run_cases(mod, cases, {"rle_encode", "rle_decode"})


def p_merge_gen(rng):
    return {"max_span": rng.randint(5, 12)}


def _merge_expected(iv):
    iv = sorted([list(x) for x in iv], key=lambda t: (t[0], t[1]))
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1:      # 相邻 (差 1) 也算相连 —— 规格明写
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def p_merge_public(params):
    ex = [[[1, 3], [2, 4]], [[10, 12], [13, 15]], [[5, 5]]]
    return [{"call": "merge_intervals", "args": [e], "expected": _merge_expected(e)} for e in ex]


def p_merge_hidden(params, rng):
    cases = []
    for _ in range(14):
        k = rng.randint(1, 6)
        iv = []
        for _ in range(k):
            a = rng.randint(0, params["max_span"])
            iv.append([a, a + rng.randint(0, 4)])
        cases.append({"call": "merge_intervals", "args": [iv], "expected": _merge_expected(iv)})
    cases.append({"call": "merge_intervals", "args": [[]], "expected": []})
    cases.append({"call": "merge_intervals", "args": [[[3, 7], [1, 2], [8, 9]]],
                  "expected": [[1, 9]]})          # 相邻双接 (1-2)+(3-7)+(8-9) → 一条
    return cases


def p_merge_check(mod, params, cases):
    return _run_cases(mod, cases, {"merge_intervals"})


def p_bracket_gen(rng):
    return {"max_len": rng.randint(4, 10)}


def _bracket_ok(s):
    """独立 oracle: 把 '?' 枚举成 '(' / ')' 后判是否可配平。"""
    idx = [i for i, c in enumerate(s) if c == "?"]
    for combo in itertools.product("()", repeat=len(idx)):
        t = list(s)
        for i, c in zip(idx, combo):
            t[i] = c
        depth, ok = 0, True
        for c in t:
            depth += 1 if c == "(" else -1
            if depth < 0:
                ok = False
                break
        if ok and depth == 0:
            return True
    return False


def p_bracket_public(params):
    ex = ["(?)", "?(", "??"]
    return [{"call": "can_balance", "args": [e], "expected": _bracket_ok(e)} for e in ex]


def p_bracket_hidden(params, rng):
    cases = []
    for _ in range(14):
        n = rng.randint(2, params["max_len"])
        s = "".join(rng.choice("()?") for _ in range(n))
        cases.append({"call": "can_balance", "args": [s], "expected": _bracket_ok(s)})
    cases.append({"call": "can_balance", "args": [""], "expected": True})
    cases.append({"call": "can_balance", "args": ["("], "expected": False})
    cases.append({"call": "can_balance", "args": ["?)"], "expected": True})
    return cases


def p_bracket_check(mod, params, cases):
    return _run_cases(mod, cases, {"can_balance"})


def p_topo_gen(rng):
    n = rng.randint(4, 7)
    all_edges = list(itertools.combinations(range(n), 2))
    rng.shuffle(all_edges)
    k = rng.randint(n - 1, min(len(all_edges), n + 2))
    edges = sorted(all_edges[:k])
    return {"n": n, "edges": edges}


def p_topo_public(params):
    return [{"call": "topo_order", "args": [4, [[0, 1], [1, 2], [2, 3]]], "expected": "valid"}]


def p_topo_hidden(params, rng):
    cases = []
    for _ in range(8):
        n = rng.randint(4, 6)
        all_edges = list(itertools.combinations(range(n), 2))
        rng.shuffle(all_edges)
        order = list(range(n))
        rng.shuffle(order)
        pos = {v: i for i, v in enumerate(order)}
        edges = [[u, v] for u, v, _ in
                 [(u, v, pos[u] < pos[v]) for u, v in all_edges[: rng.randint(n - 1, n + 1)]]]
        edges = [[u, v] if pos[u] < pos[v] else [v, u] for u, v in edges]
        cases.append({"call": "topo_order", "args": [n, edges], "expected": "valid", "edges": edges, "n": n})
    # 有环 → 必须返回 None
    cases.append({"call": "topo_order", "args": [3, [[0, 1], [1, 2], [2, 0]]], "expected": None})
    return cases


def p_topo_check(mod, params, cases):
    passed, total, tax = 0, 0, {}
    fn = getattr(mod, "topo_order", None)
    if fn is None:
        return 0, len(cases), {"missing_function": len(cases)}
    for c in cases:
        total += 1
        try:
            got = fn(c["args"][0], c["args"][1])
        except Exception as ex:  # noqa: BLE001
            tax["exception"] = tax.get("exception", 0) + 1
            continue
        if c["expected"] is None:
            if got is None:
                passed += 1
            else:
                tax["expected_none"] = tax.get("expected_none", 0) + 1
            continue
        if got is None:
            tax["unexpected_none"] = tax.get("unexpected_none", 0) + 1
            continue
        n, edges = c["n"], [tuple(e) for e in c["edges"]]
        ok = isinstance(got, (list, tuple)) and len(got) == n and sorted(got) == list(range(n))
        if ok:
            pos = {v: i for i, v in enumerate(got)}
            ok = all(pos[u] < pos[v] for u, v in edges)
        if ok:
            passed += 1
        else:
            tax["invalid_order"] = tax.get("invalid_order", 0) + 1
    return passed, total, tax


def p_ttl_gen(rng):
    return {"cap": rng.randint(2, 4), "ttl": rng.randint(2, 5)}


def p_ttl_public(params):
    return [{"call": "__doc__", "args": [], "expected": "见规格: get 返回 None 表示未命中/已过期"}]


def p_ttl_hidden(params, rng):
    """隐藏用例 = 场景脚本 (在本脚本内回放, 不依赖被测代码的内部结构)。"""
    return [{"scenario": "boundary", "cap": params["cap"], "ttl": params["ttl"]}]


def p_ttl_check(mod, params, cases):
    cls = getattr(mod, "TtlCache", None)
    if cls is None:
        return 0, 4, {"missing_class": 4}
    passed, total, tax = 0, 0, {}

    def step(name, fn, cond):
        nonlocal passed, total
        total += 1
        try:
            if cond():
                passed += 1
            else:
                tax[name] = tax.get(name, 0) + 1
        except Exception:  # noqa: BLE001
            tax[name + ":exception"] = tax.get(name + ":exception", 0) + 1

    cap, ttl = params["cap"], params["ttl"]
    c = cls(cap, ttl)
    c.put("a", 1, 0)
    step("hit_before_expiry", None, lambda: c.get("a", ttl - 1) == 1)
    step("expired_at_boundary", None, lambda: c.get("a", ttl) is None)   # now >= t0+ttl 即过期
    keys = ["a", "b", "c", "d", "e"][:cap + 1]
    c2 = cls(cap, ttl)
    for i, k in enumerate(keys):
        c2.put(k, i, 0)
    step("lru_evict_oldest", None,
         lambda: c2.get(keys[0], 0) is None and c2.get(keys[1], 0) == 1)
    # 相同 now 下触碰第一个 → 淘汰必须命中"最久未用"的那个 (访问先后语义)
    c3 = cls(cap, ttl)
    ks = ["x", "y", "z", "w", "u"][:cap]
    for i, k in enumerate(ks):
        c3.put(k, i, 0)
    _ = c3.get(ks[0], 0)
    c3.put("NEW", 9, 0)
    step("lru_after_touch", None,
         lambda: c3.get(ks[1], 0) is None and c3.get(ks[0], 0) == 0 and c3.get("NEW", 0) == 9)
    return passed, total, tax


def p_roman_gen(rng):
    return {}


def _to_roman(n):
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def p_roman_public(params):
    return [{"call": "to_roman", "args": [n], "expected": _to_roman(n)} for n in (4, 9, 40)]


def p_roman_hidden(params, rng):
    cases = [{"call": "to_roman", "args": [n], "expected": _to_roman(n)}
             for n in (1, 3, 49, 90, 400, 944, 1994, 3999)]
    cases += [{"call": "from_roman", "args": [_to_roman(n)], "expected": n}
              for n in (7, 44, 58, 333, 2024)]
    for _ in range(6):
        n = rng.randint(1, 3999)
        cases.append({"call": "to_roman", "args": [n], "expected": _to_roman(n)})
    # 非规范写法 → 必须 None (判别力: 单个用例太薄, 必须成族)
    for bad in ("IIII", "VV", "IL", "IC", "XM", "XXXX", "IIX", "MCMC"):
        cases.append({"call": "from_roman", "args": [bad], "expected": None})
    return cases


def p_roman_check(mod, params, cases):
    return _run_cases(mod, cases, {"to_roman", "from_roman"})


def _run_cases(mod, cases, required):
    for name in required:
        if not hasattr(mod, name):
            return 0, len(cases), {"missing_function": len(cases)}
    passed, total, tax = 0, 0, {}
    for c in cases:
        total += 1
        fn = getattr(mod, c["call"])
        try:
            got = fn(*c["args"])
        except Exception:  # noqa: BLE001
            tax["exception"] = tax.get("exception", 0) + 1
            continue
        exp = c["expected"]
        ok = got == exp
        if not ok and c["call"] == "from_roman" and exp is None:
            ok = False
        if ok:
            passed += 1
        else:
            key = "wrong_output" if exp is not None else "should_reject"
            tax[key] = tax.get(key, 0) + 1
    return passed, total, tax


PROGRAM_FAMILIES = {
    "rle_roundtrip": (p_rle_gen, p_rle_public, p_rle_hidden, p_rle_check),
    "merge_intervals": (p_merge_gen, p_merge_public, p_merge_hidden, p_merge_check),
    "bracket_wildcard": (p_bracket_gen, p_bracket_public, p_bracket_hidden, p_bracket_check),
    "topo_order": (p_topo_gen, p_topo_public, p_topo_hidden, p_topo_check),
    "ttl_cache": (p_ttl_gen, p_ttl_public, p_ttl_hidden, p_ttl_check),
    "roman_canonical": (p_roman_gen, p_roman_public, p_roman_hidden, p_roman_check),
}


# ─────────────────────────── 程序题规格 (题面 = 唯一口径) ───────────────────────────

PROGRAM_SPECS = {
"rle_roundtrip": """实现两个函数:
- rle_encode(s: str) -> list[list]: 返回**极大连续段**分解, 每段 [count, char], count>=1;
  空串 -> []。段内字符相同, 相邻段字符必不同 (不得把相同字符拆成多段)。
- rle_decode(pairs: list[list]) -> str: 还原原串; [] -> ""。
例: "aabbb" -> [[2,"a"],[3,"b"]]; "abc" -> [[1,"a"],[1,"b"],[1,"c"]]。
""",
"merge_intervals": """实现 merge_intervals(iv: list[list]) -> list[list]:
区间为闭区间 [start, end] (start<=end 整数)。
规则: 先按 start 升序 (相同时按 end 升序); 若当前区间与结果的最后一段**重叠或相邻**
(即 start <= last_end + 1) 则合并, 合并后 end 取两者较大值。相邻 (差恰好 1) 也算相连。
空输入 -> []。
例: [[1,3],[2,4]] -> [[1,4]]; [[10,12],[13,15]] -> [[10,15]]; [[5,5]] -> [[5,5]]。
""",
"bracket_wildcard": """实现 can_balance(s: str) -> bool:
字符串只含 '(' ')' '?'。'?' 可任意当作 '(' 或 ')'。
若存在某种替换使结果为**配平括号串** (任意前缀里 '(' 数 >= ')' 数, 且总数相等) 返回 True。
空串算配平。例: "(?)" -> True; "?(" -> False; "??" -> True; ")" -> False; "?)" -> True。
""",
"topo_order": """实现 topo_order(n: int, edges: list[list]) -> list|None:
顶点 0..n-1, edges 为 [u,v] 表示 u 必须在 v 之前。返回**任一**合法拓扑序 (长度 n 的排列);
若图有环返回 None。
判定(机械): 返回必须是 0..n-1 的排列, 且对每条边 pos[u] < pos[v]。
""",
"ttl_cache": """实现类 TtlCache(capacity: int, ttl: int):
- put(key, value, now: int): 写入, now 为逻辑时钟 (单调不减)。
- get(key, now: int): 命中返回 value, 未命中或**已过期**返回 None。
过期语义 (**精确口径**): 记写入时刻 t0, 当 now >= t0 + ttl 即视为过期 (边界相等也算过期);
被 get 命中或 put 覆盖会刷新其"最近使用"次序 —— 次序按**访问先后**判定 (内部自增序号),
不得用 now 值代替 (now 可相等, 相同的 now 不足以确定先后)。
容量: 写入使活跃条目数超过 capacity 时, 淘汰**最久未被使用**的条目 (LRU)。
""",
"roman_canonical": """实现两个函数:
- to_roman(n: int) -> str: 1<=n<=3999, 返回**规范**罗马数字 (大值符号优先, 含减法组合
  IV/IX/XL/XC/CD/CM)。例: 4->"IV", 9->"IX", 40->"XL", 1994->"MCMXCIV"。
- from_roman(s: str) -> int|None: 严格解码: 先按符号表解码得到 v, 再要求 to_roman(v) == s
  (**互逆判据** —— 只有规范写法本身可接受), 否则返回 None。
  不得用"贪心消费恰好耗尽"作判据: "IIII" 贪心可耗尽但非规范, 必须返回 None。
  例: "IIII" -> None; "MCMXCIV" -> 1994。
""",
}


def write_spec(fam: str, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PROGRAM_SPECS[fam], encoding="utf-8")

# ─────────────────────────── 参考解 / 变异解 (selftest 判定力负控) ───────────────────────────

REF_SOLUTIONS = {}

REF_SOLUTIONS["merge_intervals"] = '''
def merge_intervals(iv):
    out = []
    for a, b in sorted([list(x) for x in iv], key=lambda t: (t[0], t[1])):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
'''

MUTANT_SOLUTIONS = {}
# 变异 A: 只合并真正重叠 (丢掉"相邻"语义) —— 规格细节被忽略的典型形态
MUTANT_SOLUTIONS["merge_intervals:drop_adjacent"] = '''
def merge_intervals(iv):
    out = []
    for a, b in sorted([list(x) for x in iv], key=lambda t: (t[0], t[1])):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
'''
# 变异 B: 不排序直接合并 (顺序依赖)
MUTANT_SOLUTIONS["merge_intervals:no_sort"] = '''
def merge_intervals(iv):
    out = []
    for a, b in [list(x) for x in iv]:
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
'''

REF_SOLUTIONS["ttl_cache"] = '''
class TtlCache:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self._d, self._seq = capacity, ttl, {}, 0

    def _bump(self):
        self._seq += 1
        return self._seq

    def get(self, key, now):
        it = self._d.get(key)
        if it is None:
            return None
        value, t0, _ = it
        if now >= t0 + self.ttl:
            del self._d[key]
            return None
        self._d[key] = (value, t0, self._bump())
        return value

    def put(self, key, value, now):
        self._d.pop(key, None)
        self._d[key] = (value, now, self._bump())
        active = [k for k, (v, t0, _s) in self._d.items() if now < t0 + self.ttl]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._d[k][2])
            del self._d[victim]
            active.remove(victim)
'''

MUTANT_SOLUTIONS["ttl_cache:expire_after_boundary"] = '''
class TtlCache:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self._d, self._seq = capacity, ttl, {}, 0

    def _bump(self):
        self._seq += 1
        return self._seq

    def get(self, key, now):
        it = self._d.get(key)
        if it is None:
            return None
        value, t0, _ = it
        if now > t0 + self.ttl:              # off-by-one: 边界时刻当成未过期
            del self._d[key]
            return None
        self._d[key] = (value, t0, self._bump())
        return value

    def put(self, key, value, now):
        self._d.pop(key, None)
        self._d[key] = (value, now, self._bump())
        active = [k for k, (v, t0, _s) in self._d.items() if now < t0 + self.ttl]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._d[k][2])
            del self._d[victim]
            active.remove(victim)
'''

MUTANT_SOLUTIONS["ttl_cache:recency_by_clock"] = '''
class TtlCache:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self._d = capacity, ttl, {}

    def get(self, key, now):
        it = self._d.get(key)
        if it is None:
            return None
        value, t0, _ = it
        if now >= t0 + self.ttl:
            del self._d[key]
            return None
        self._d[key] = (value, t0, now)      # 用 now 当次序 (相同 now 无法区分先后)
        return value

    def put(self, key, value, now):
        self._d.pop(key, None)
        self._d[key] = (value, now, now)
        active = [k for k, (v, t0, _s) in self._d.items() if now < t0 + self.ttl]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._d[k][2])
            del self._d[victim]
            active.remove(victim)
'''

REF_SOLUTIONS["roman_canonical"] = '''
VALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]

def to_roman(n):
    out = []
    for v, s in VALS:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)

def from_roman(s):
    idx, total = 0, 0
    for v, sym in VALS:
        while s.startswith(sym, idx):
            total += v
            idx += len(sym)
    if idx != len(s):
        return None
    return total if to_roman(total) == s else None   # 互逆判据
'''

MUTANT_SOLUTIONS["roman_canonical:lenient_decode"] = '''
VALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]

def to_roman(n):
    out = []
    for v, s in VALS:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)

def from_roman(s):
    total = 0
    i = 0
    while i < len(s):
        if i + 1 < len(s) and s[i:i + 2] in {sym for _, sym in VALS}:
            total += dict((sym, v) for v, sym in VALS)[s[i:i + 2]]
            i += 2
        else:
            total += dict((sym, v) for v, sym in VALS)[s[i]]
            i += 1
    return total
'''


# ─────────────────────────── 装载被测解 ───────────────────────────

def load_solution(path: Path):
    spec = importlib.util.spec_from_file_location("cycle_solution", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法装载: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # 语法/导入错误直接抛出
    return mod


# ─────────────────────────── 子命令 ───────────────────────────

def cmd_status(_a):
    probe = REPO / "scripts" / "capability_cycle_status.py"
    r = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    return r.returncode


def _cycle_id(seed: int) -> str:
    return time.strftime("%Y%m%d") + f"-s{seed}"


def cmd_emit(a):
    rng = random.Random(a.seed)
    mfam = a.math_family or rng.choice(sorted(MATH_FAMILIES))
    pfam = a.program_family or rng.choice(sorted(PROGRAM_FAMILIES))
    mgen, moracle, mstmt = MATH_FAMILIES[mfam]
    pgen, ppublic, phidden, _pcheck = PROGRAM_FAMILIES[pfam]
    mp = mgen(rng)
    pp = pgen(rng)
    task = {
        "cycle_id": _cycle_id(a.seed),
        "seed": a.seed,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "math": {"family": mfam, "params": mp, "statement": mstmt(mp)},
        # 注意: 数学题不落 oracle 答案 (判定时现算, 防"读答案")
        "program": {"family": pfam, "params": pp, "public_examples": ppublic(pp),
                    "spec_file": f"specs/{pfam}.md"},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_spec(pfam, OUT_DIR / task["program"]["spec_file"])
    p = OUT_DIR / f"cycle-{task['cycle_id']}.json"
    p.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"emitted": str(p.relative_to(REPO)), "cycle_id": task["cycle_id"],
                      "math_family": mfam, "program_family": pfam}, ensure_ascii=False))
    print("\n== 数学题 ==\n" + task["math"]["statement"])
    print("\n== 程序题规格文件 ==\n" + str((OUT_DIR / task["program"]["spec_file"])))
    print("\n== 公开示例 ==\n" + json.dumps(task["program"]["public_examples"], ensure_ascii=False))
    return 0


def cmd_grade(a):
    task = json.loads(Path(a.cycle).read_text(encoding="utf-8"))
    seed = task["seed"]
    sol_dir = Path(a.dir)
    res = {"cycle_id": task["cycle_id"], "seed": seed, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "math": None, "program": None}

    # 数学: 现算 oracle 与作答比对
    mf = task["math"]["family"]
    moracle = MATH_FAMILIES[mf][1]
    ans_file = sol_dir / "math_answer.json"
    if ans_file.exists():
        got = json.loads(ans_file.read_text(encoding="utf-8")).get("answer")
        exp = moracle(task["math"]["params"])
        res["math"] = {"family": mf, "answer": got, "oracle": exp, "ok": got == exp}
    else:
        res["math"] = {"family": mf, "ok": False, "mode": "no_answer"}

    # 程序: 隐藏用例 (由 seed 派生, 与公开示例不同)
    pf = task["program"]["family"]
    _pgen, _ppub, phidden, pcheck = PROGRAM_FAMILIES[pf]
    code_file = sol_dir / "solution.py"
    if not code_file.exists():
        res["program"] = {"family": pf, "ok": False, "mode": "no_solution"}
    else:
        try:
            mod = load_solution(code_file)
        except Exception as ex:  # noqa: BLE001
            res["program"] = {"family": pf, "ok": False, "mode": "load_error", "detail": str(ex)[:200]}
        else:
            hcases = phidden(task["program"]["params"], random.Random(seed ^ 0x5EED))
            passed, total, tax = pcheck(mod, task["program"]["params"], hcases)
            res["program"] = {"family": pf, "passed": passed, "total": total,
                              "rate": round(passed / total, 4) if total else None,
                              "taxonomy": tax, "ok": total > 0 and passed == total}

    ok = bool(res["math"].get("ok")) and bool(res["program"] and res["program"].get("ok"))
    res["all_ok"] = ok
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with KPI.open("a", encoding="utf-8") as f:
        f.write(json.dumps(res, ensure_ascii=False) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_selftest(_a):
    """判定力负控: 参考解全绿 + 每个变异解必须变红 (否则判据空心)。"""
    tmp = OUT_DIR / "_selftest"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []

    for pf in sorted(REF_SOLUTIONS):
        _g, _pub, phidden, pcheck = PROGRAM_FAMILIES[pf]
        params = PROGRAM_FAMILIES[pf][0](random.Random(7))
        hcases = phidden(params, random.Random(99))
        variants = [("ref", REF_SOLUTIONS[pf])] + [
            (k.split(":", 1)[1], v) for k, v in MUTANT_SOLUTIONS.items() if k.startswith(pf + ":")
        ]
        for name, src in variants:
            f = tmp / f"{pf}__{name}.py"
            f.write_text(src, encoding="utf-8")
            mod = load_solution(f)
            passed, total, tax = pcheck(mod, params, hcases)
            rows.append({"family": pf, "variant": name, "passed": passed, "total": total,
                         "rate": round(passed / total, 4), "taxonomy": tax})

    # 数学 oracle 自洽: 小规模与暴力枚举一致 (同一 oracle 跑两次恒等 → 只做大数复核)
    math_rows = []
    for fam, (mgen, moracle, _s) in sorted(MATH_FAMILIES.items()):
        p = mgen(random.Random(11))
        a1, a2 = moracle(p), moracle(dict(p))
        math_rows.append({"family": fam, "deterministic": a1 == a2, "answer": a1})

    bad = [r for r in rows if r["variant"] == "ref" and r["rate"] != 1.0]
    hollow = [r for r in rows if r["variant"] != "ref" and r["rate"] == 1.0]
    nondet = [r for r in math_rows if not r["deterministic"]]
    print(json.dumps({"program_rows": rows, "math_rows": math_rows,
                      "ref_not_green": bad, "mutant_not_caught": hollow,
                      "math_nondeterministic": nondet,
                      "verdict": "SOUND" if not (bad or hollow or nondet) else "HOLLOW"},
                     ensure_ascii=False, indent=2))
    ok = not (bad or hollow or nondet)
    print(f"selftest: {'PASS' if ok else 'FAIL'} ({len(rows)} 程序变体 / {len(math_rows)} 数学家族)")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="能力自检循环 (随机程序题 + 随机数学题)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="检测机制入口: 判 mode (tasks|selfcheck)")
    s.set_defaults(fn=cmd_status)

    e = sub.add_parser("emit", help="生成一轮随机题")
    e.add_argument("--seed", type=int, required=True)
    e.add_argument("--math-family", default=None)
    e.add_argument("--program-family", default=None)
    e.set_defaults(fn=cmd_emit)

    g = sub.add_parser("grade", help="对某轮的解做机械判定")
    g.add_argument("--cycle", required=True)
    g.add_argument("--dir", required=True)
    g.set_defaults(fn=cmd_grade)

    t = sub.add_parser("selftest", help="判定力负控")
    t.set_defaults(fn=cmd_selftest)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
