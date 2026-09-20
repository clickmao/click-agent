def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            na, nb = a - i, b - j
            if _losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    phi = (1 + 5 ** 0.5) / 2
    return a == int(d * phi)
