"""Independent cross-check: brute-force game solvers vs the games package.

Run from the working root:  python3 games/_selftest.py   (exit 0 = PASS)
"""
import os
import sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games import life, sub, nim, wythoff


def bf_life(h, w, k, grid):
    g = [[c == "#" for c in row] for row in grid]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = sum(1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                        if not (dx == 0 and dy == 0)
                        and 0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx])
                nxt[y][x] = (n == 2 or n == 3) if g[y][x] else (n == 3)
        g = nxt
    return "\n".join("".join("#" if c else "." for c in r) for r in g)


@lru_cache(maxsize=None)
def bf_sub(n, steps):
    for s in steps:
        if s <= n and not bf_sub(n - s, steps):
            return True
    return False


@lru_cache(maxsize=None)
def bf_nim(piles):
    piles = tuple(piles)
    for i in range(len(piles)):
        for take in range(1, piles[i] + 1):
            nxt = list(piles)
            nxt[i] -= take
            if sum(nxt) and not bf_nim(tuple(nxt)):
                return True
    return False


@lru_cache(maxsize=None)
def bf_wythoff(a, b):
    if a > b:
        a, b = b, a
    for i in range(1, a + 1):
        if not bf_wythoff(a - i, b):
            return True
    for j in range(1, b + 1):
        if not bf_wythoff(a, b - j):
            return True
    for t in range(1, min(a, b) + 1):
        if not bf_wythoff(a - t, b - t):
            return True
    return False


fails = 0


def check(name, cond, detail=""):
    global fails
    if not cond:
        fails += 1
        print("FAIL", name, detail)


import itertools, random
random.seed(12345)

# life: exhaustive small grids
for h in (1, 2, 3):
    for w in (1, 2, 3):
        for k in (0, 1, 2):
            for bits in range(1 << (h * w)):
                grid = ["".join("#" if (bits >> (y * w + x)) & 1 else "." for x in range(w))
                        for y in range(h)]
                text = "%d %d %d\n%s\n" % (h, w, k, "\n".join(grid))
                check("life", life.solve(text) == bf_life(h, w, k, grid), (h, w, k, grid))

# sub: random step sets containing 1
for _ in range(300):
    k = random.randint(1, 6)
    steps = tuple(sorted(set([1] + [random.randint(1, 12) for _ in range(k - 1)])))
    n = random.randint(1, 60)
    text = "%d %d\n%s\n" % (n, len(steps), " ".join(map(str, steps)))
    got = sub.solve(text)
    if bf_sub(n, steps):
        small = min(s for s in steps if s <= n and not bf_sub(n - s, steps))
        exp = "WIN %d" % small
    else:
        exp = "LOSE"
    check("sub", got == exp, (n, steps, got, exp))

# nim: piles 1..9, 1..3 piles
for m in (1, 2, 3):
    for piles in itertools.product(range(1, 10), repeat=m):
        text = "%d\n%s\n" % (m, " ".join(map(str, piles)))
        got = nim.solve(text)
        if not bf_nim(tuple(piles)):
            check("nim", got == "LOSE", (piles, got))
        else:
            exp = None
            for idx in range(m):
                for take in range(1, piles[idx] + 1):
                    nxt = list(piles)
                    nxt[idx] -= take
                    if not bf_nim(tuple(nxt)):
                        exp = "WIN %d %d" % (idx + 1, take)
                        break
                if exp:
                    break
            check("nim", got == exp, (piles, got, exp))

# wythoff: full 1..25 grid
for a in range(1, 26):
    for b in range(1, 26):
        got = wythoff.solve("%d %d\n" % (a, b))
        if not bf_wythoff(a, b):
            check("wythoff", got == "LOSE", (a, b, got))
        else:
            exp = None
            for i in range(0, a + 1):
                for j in range(0, b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0 and i != j:
                        continue
                    if not bf_wythoff(a - i, b - j):
                        exp = "WIN %d %d" % (i, j)
                        break
                if exp:
                    break
            check("wythoff", got == exp, (a, b, got, exp))

print("ALL PASS" if fails == 0 else "FAILS=%d" % fails)
sys.exit(0 if fails == 0 else 1)
