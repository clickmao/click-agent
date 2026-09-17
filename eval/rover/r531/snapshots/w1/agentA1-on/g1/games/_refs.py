"""Shared reference models for verification (independent of games/*.py logic)."""

from functools import lru_cache

import math


def ref_life(text):
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    g = [[1 if ch == "#" else 0 for ch in lines[1 + r][:w]] for r in range(h)]
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += g[rr][cc]
                ng[r][c] = 1 if (g[r][c] and n in (2, 3)) or (not g[r][c] and n == 3) else 0
        g = ng
    return "\n".join("".join("#" if v else "." for v in row) for row in g)


def ref_sub(n, moves):
    @lru_cache(maxsize=None)
    def win(x):
        return any(s <= x and not win(x - s) for s in moves)
    if not win(n):
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win(n - s):
            return "WIN %d" % s
    return "LOSE"


def ref_nim(piles):
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    moves = []
    for idx, a in enumerate(piles):
        for r in range(1, a + 1):
            rest = list(piles)
            rest[idx] = a - r
            x = 0
            for v in rest:
                x ^= v
            if x == 0:
                moves.append((idx + 1, r))
    return "WIN %d %d" % min(moves)


@lru_cache(maxsize=None)
def _wy_win(x, y):
    x, y = (x, y) if x <= y else (y, x)
    for i in range(1, x + 1):
        if not _wy_win(x - i, y):
            return True
    for j in range(1, y + 1):
        if not _wy_win(x, y - j):
            return True
    for t in range(1, x + 1):
        if not _wy_win(x - t, y - t):
            return True
    return False


def wy_losing(a, b):
    """Independent P-position test via Beatty sequences (exact integer floor)."""
    lo, hi = (a, b) if a <= b else (b, a)
    if lo == 0 and hi == 0:
        return True
    # A position is P iff (lo, hi) == (floor(k*phi), floor(k*phi^2)) for some k.
    k = math.isqrt(5 * lo * lo)
    if (lo + k) % 2 != 0:
        k -= 1
    if (lo + k) // 2 != lo:  # not floor(k*phi): check candidate k = floor(lo/phi) + 1
        pass
    # solve k from lo = floor(k*phi): k = floor(lo/phi + 1) candidates
    for cand in (int(lo * 2 / (1 + 5 ** 0.5)) - 1, int(lo * 2 / (1 + 5 ** 0.5)),
                 int(lo * 2 / (1 + 5 ** 0.5)) + 1):
        if cand <= 0:
            continue
        s = math.isqrt(5 * cand * cand)
        if (cand + s) % 2 != 0:
            s -= 1
        kk = (cand + s) // 2
        if kk == lo and lo + cand == hi:
            return True
    return False


def ref_wythoff(a, b):
    """Lexicographically smallest legal move whose resulting position is a P-position.

    Uses the independently-constructed P-position set (Beatty), not the game tree.
    """
    if wy_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            legal = (j == 0 and i >= 1) or (i == 0 and j >= 1) or (i == j)
            if not legal:
                continue
            if wy_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
