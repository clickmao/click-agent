def _is_lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    t = int(d * ((5 ** 0.5 + 1) / 2))
    return t == a


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if _is_lose(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
                    break
        else:
            continue
        break
    return 'WIN %d %d' % best
