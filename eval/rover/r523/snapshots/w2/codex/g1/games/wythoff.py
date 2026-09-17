def solve(text: str) -> str:
    a, b = map(int, text.split())

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if not ((i == 0 or j == 0 or i == j)):
                continue
            if wythoff_lose(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def wythoff_lose(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    n = y - x
    target = int(((5 ** 0.5 + 1) / 2) * n)
    return x == target or x == target - 1
