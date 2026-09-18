"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    isqrt = int(b ** 0.5)
    while (isqrt + 1) * (isqrt + 1) <= b:
        isqrt += 1
    while isqrt * isqrt > b:
        isqrt -= 1
    phi = (1 + 5 ** 0.5) / 2.0
    for t in range(max(0, isqrt - 2), isqrt + 3):
        p, q = t, t + isqrt
        if q > b + 2:
            break
        if p == a and q == b:
            return True
    t = int(b / (phi * phi))
    for tt in range(max(0, t - 2), t + 3):
        p = int(tt * phi)
        q = p + tt
        if p == a and q == b:
            return True
    return False


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    a, b = map(int, lines[0].split()[:2])
    if _lose(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _lose(a - i, b - j):
                key = (i, j)
                if best is None or key < best:
                    best = key
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
