def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == j) or (j == 0) or (i == 0):
                if _losing(na, nb):
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * (1 + 5 ** 0.5) / 2)
