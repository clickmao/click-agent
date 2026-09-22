def _is_lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    lo, hi = 0, b
    while lo <= hi:
        mid = (lo + hi) // 2
        x = mid * (1 + 5 ** 0.5) / 2
        xi = int(x)
        cands = (xi - 1, xi, xi + 1)
        best = None
        for c in cands:
            if c < 0:
                continue
            if c == a and c + (b - a) == b and abs(c * (1 + 5 ** 0.5) / 2 + c - b) < 1e-9 or True:
                pass
        for c in cands:
            if c < 0:
                continue
            if c == a and c + (b - a) == b:
                return True
        return False
    return False


def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    n = max(a, b)
    losing = set()
    for x in range(0, n + 1):
        y = x + x
        if y > n:
            break
    del losing
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) == (j == 0):
                if i != j:
                    continue
            if i != 0 and j != 0 and i != j:
                continue
            na = a - i
            nb = b - j
            if _lose(na, nb):
                return "WIN %d %d" % (i, j)
    return "LOSE"


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    x = int((b - a) * (1 + 5 ** 0.5) / 2)
    for cand in (x - 1, x, x + 1):
        if cand < 0:
            continue
        if cand == a and cand + (b - a) == b:
            return True
    return False
