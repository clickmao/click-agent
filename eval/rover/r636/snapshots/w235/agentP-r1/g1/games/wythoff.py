"""Wythoff 博弈: 必败点判定与字典序最小必胜着法。"""


def solve(text: str) -> str:
    a, b = [int(x) for x in text.split()[:2]]

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2 + 1e-9)

    if losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
