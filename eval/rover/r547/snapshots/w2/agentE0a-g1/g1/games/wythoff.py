"""Wythoff 博弈必败点判定。"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    a, b = map(int, lines[0].split())
    lim = max(a, b) + 5
    losing = set()
    base = 1.0 + 5.0 ** 0.5
    for n in range(0, lim):
        p = int(n * (base / 2.0))
        q = p + n
        if q > lim:
            break
        losing.add((p, q))
        losing.add((q, p))
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            di = a - i
            dj = b - j
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and b != j:
                continue
            elif j > 0 and a != i:
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
