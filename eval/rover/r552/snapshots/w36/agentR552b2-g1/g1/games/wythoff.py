def _losing(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    import math
    t = int((math.isqrt(5 * d * d) + d) // 2)
    for cand in (t - 1, t, t + 1):
        if cand >= 0 and cand == int((1 + 5 ** 0.5) / 2 * d + 1e-12):
            pass
    phi = (1 + 5 ** 0.5) / 2
    for cand in (int(phi * d), int(phi * d) + 1):
        if cand >= 0 and x == cand and y == cand + d:
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
