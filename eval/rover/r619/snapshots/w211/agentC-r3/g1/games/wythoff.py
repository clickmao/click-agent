"""Wythoff 博弈必败点判定。"""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a

    sq5 = 5 ** 0.5
    n = int((b - a) * (1 + sq5) / 2)
    for cand in (n - 1, n, n + 1):
        if cand >= 0 and int(cand * (1 + sq5) / 2) == a and int(cand * (3 + sq5) / 2) == b:
            return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i > a or j > b:
                continue
            na, nb = a - i, b - j
            lo, hi = (na, nb) if na <= nb else (nb, na)
            nn = int((hi - lo) * (1 + sq5) / 2)
            is_lose = False
            for cand in (nn - 1, nn, nn + 1):
                if cand >= 0 and int(cand * (1 + sq5) / 2) == lo and int(cand * (3 + sq5) / 2) == hi:
                    is_lose = True
                    break
            if is_lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return 'WIN %d %d' % (i, j)
