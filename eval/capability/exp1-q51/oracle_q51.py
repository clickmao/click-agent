#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q51 独立 oracle: 由**题面逐字** (eval/rover/r540/run-w1/task-g1-prompt.txt) 重写的四款游戏
参考解, 用作夹具自洽正控 (P2) 与最小修复实验的对照实现。

纪律:
  · 与被测产物**零共享代码** (不 import snapshots 下任何件);
  · 不读 cases-r521.json 的 expected_stdout (oracle 先独立算出, 再与用例比对);
  · 负控开关 --broken-wythoff-cold 复现产物同款错误冷点构造 (P6), 用于证明本 oracle 非恒真门。
"""
import sys

PHI = (1 + 5 ** 0.5) / 2


def life(text):
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
        ng = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                alive = grid[r][c] == "#"
                ng[r][c] = "#" if (cnt == 3 or (alive and cnt == 2)) else "."
        grid = ng
    return "\n".join("".join(row) for row in grid)


def sub(text):
    toks = text.split()
    n, k = int(toks[0]), int(toks[1])
    moves = sorted(int(x) for x in toks[2:2 + k])
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"


def nim(text):
    toks = text.split()
    m = int(toks[0])
    piles = [int(x) for x in toks[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"


def _cold_pairs(limit):
    """标准 Wythoff 冷点集: (floor(n*phi), floor(n*phi^2)); 用整数递推避免浮点误差。"""
    pairs = set()
    used = set()
    a = 0
    n = 0
    while a <= limit:
        b = a + n
        pairs.add((a, b))
        used.add(a)
        used.add(b)
        n += 1
        a = int(n * PHI)
        while a in used:
            a += 1
    pairs.add((0, 0))
    return pairs


def _broken_cold_pairs(limit):
    """产物同款错误构造 (负控, P6): b = a + len(pairs) + 1, 从 a=0,b=1 起步。"""
    pairs, seen, a = set(), set(), 0
    while True:
        while a in seen:
            a += 1
        b = a + len(pairs) + 1
        if b > limit:
            break
        pairs.add((a, b))
        seen.add(a)
        seen.add(b)
        a += 1
    return pairs


def wythoff(text, broken=False):
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    lim = max(a, b) + 1
    cold = _broken_cold_pairs(lim * 4) if broken else _cold_pairs(lim * 4)

    def is_cold(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        return (lo, hi) in cold

    if is_cold(a, b):
        return "LOSE"
    cands = []
    for i in range(1, a + 1):
        if is_cold(a - i, b):
            cands.append((i, 0))
    for j in range(1, b + 1):
        if is_cold(a, b - j):
            cands.append((0, j))
    for d in range(1, min(a, b) + 1):
        if is_cold(a - d, b - d):
            cands.append((d, d))
    if not cands:
        return "LOSE"
    cands.sort()
    i, j = cands[0]
    return "WIN %d %d" % (i, j)


def solve(game, text, broken=False):
    if game == "life":
        return life(text)
    if game == "sub":
        return sub(text)
    if game == "nim":
        return nim(text)
    if game == "wythoff":
        return wythoff(text, broken=broken)
    raise ValueError(game)


if __name__ == "__main__":
    broken = "--broken-wythoff-cold" in sys.argv
    game = [x for x in sys.argv[1:] if not x.startswith("--")][0]
    sys.stdout.write(solve(game, sys.stdin.read(), broken=broken))
