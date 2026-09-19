def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _lose(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _lose(x, y):
    if x > y:
        x, y = y, x
    t = y - x
    return x == int(t * (1 + 5 ** 0.5) / 2)
