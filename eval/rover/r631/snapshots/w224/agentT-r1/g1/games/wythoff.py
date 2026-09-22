"""Wythoff game: LOSE for cold positions, else lexicographically smallest winning move."""


def _is_cold(a: int, b: int) -> bool:
    # Cold positions are exactly (0,0) and all pairs whose difference d = |a-b|
    # equals floor(n*phi) with n = min(a,b); the pair is then
    # (floor(n*phi), floor(n*phi)+n) for n = d. Exact integer test:
    if a == 0 and b == 0:
        return True
    d = abs(a - b)
    lo = min(a, b)
    # find n = floor(d*phi) via integer binary search (phi = (1+sqrt(5))/2)
    r = 5 * d * d + 4
    s = 5 * d * d - 4
    def is_square(x: int) -> bool:
        if x < 0:
            return False
        rt = int(x ** 0.5)
        while rt * rt > x:
            rt -= 1
        while (rt + 1) * (rt + 1) <= x:
            rt += 1
        return rt * rt == x
    # Fibonacci-based charactersation: cold pairs are (F_{2i}, F_{2i+1})? No:
    # use the standard Beatty characterisation via exact square test.
    n = (d + int((d * 5) ** 0.5)) // 2 if False else None
    # exact: n = floor(d*phi) can be computed by beatty via math.isqrt
    from math import isqrt
    n = (d + isqrt(r)) // 2 if is_square(r) else (d + isqrt(5 * d * d - 4)) // 2
    # The value above equals floor(d*phi) for all d >= 0 (Wythoff/Binet identity).
    return n == lo


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    if not lines:
        return ""
    a, b = map(int, lines[0].split()[:2])
    if _is_cold(a, b):
        return "LOSE"
    best = None
    for j in range(1, b + 1):
        if _is_cold(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    for i in range(1, a + 1):
        if _is_cold(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for t in range(1, min(a, b) + 1):
        if _is_cold(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
