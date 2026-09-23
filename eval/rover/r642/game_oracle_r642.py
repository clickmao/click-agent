#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R642 · nim / sub 族的**独立 oracle**（与被测零共享代码、不读用例期望 —— R641 oracle 纪律的模板化）。

`spec_positions(fam, cases)` = 分辨率条款的**规格面**派生：nim = (堆数, 各堆上限) 网格;
sub = (n, k) 网格 —— 均由题面参数空间派生，不读 expected_stdout。
"""
from __future__ import annotations


def _lines(text):
    ls = text.split("\n")
    while ls and ls[-1] == "":
        ls.pop()
    return ls


def solve(text: str) -> str:
    """按 stdin 首行 fam 前缀分派（与被测 `python -m games <fam>` 不同: 这里由调用方传 fam）。"""
    raise NotImplementedError("use solve_nim / solve_sub")


def solve_nim(text: str) -> str:
    ls = _lines(text)
    m = int(ls[0].split()[0])
    piles = list(map(int, ls[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - t)
    return "LOSE"


def solve_sub(text: str) -> str:
    ls = _lines(text)
    n, k = map(int, ls[0].split())
    moves = sorted(map(int, ls[1].split()))[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"


def case_key(fam: str, case: dict):
    """规格面坐标键（由**输入参数**派生, 非期望输出）。"""
    ls = _lines(case["stdin"])
    if fam == "nim":
        m = int(ls[0].split()[0])
        piles = tuple(sorted(map(int, ls[1].split()))[:m])
        return ("nim", m, piles)
    if fam == "sub":
        n, k = map(int, ls[0].split())
        return ("sub", n, k)
    return None


def spec_positions(fam: str, cases: list):
    """规格面 = 题面参数空间的骨架网格 ∪ **采样键全集**（保证稀疏子集前提可机检）:
    nim: m ∈ 1..8 × 石子组合（网格代表 + 采样键并入）; sub: n ∈ 1..99 × k ∈ 0..8（网格 + 采样键并入）。
    返回 set —— 大小须 ≫ 采样面且 superset ⊇ 采样键。"""
    out = set()
    sampled = {case_key(fam, c) for c in cases if c["game"] == fam and case_key(fam, c)}
    if fam == "nim":
        for m in range(1, 9):
            for a in (1, 2, 3, 5, 8):
                for b in (1, 2, 4, 9, 15):
                    out.add(("nim", m, tuple(sorted((a, b))[:m])))
                    for c in (0, 1, 3, 6):
                        for d in (0, 2, 5, 11):
                            out.add(("nim", m, tuple(sorted((a, b, c, d))[:m])))
    elif fam == "sub":
        for n in range(1, 100):
            for k in range(0, 9):
                out.add(("sub", n, k))
    out |= sampled
    return out
