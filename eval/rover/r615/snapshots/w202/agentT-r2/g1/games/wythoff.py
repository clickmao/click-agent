def _losing(a, b):
    x, y = min(a, b), max(a, b)
    d = y - x
    return x == int(d * 1.618033988749895)


def solve(text: str) -> str:
    tok = text.split()
    a, b = int(tok[0]), int(tok[1])
    if _losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
