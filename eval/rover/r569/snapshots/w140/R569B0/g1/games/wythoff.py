"""Wythoff 博弈: 必败判定, 必胜时给出字典序最小的着法。"""


def _lose(x, y):
    if x > y:
        x, y = y, x
    return (y - x) * (1 + 5 ** 0.5) / 2.0 < x + 1e-9


def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if _lose(a, b):
        return "LOSE"
    for i in range(a + 1):
        j = 0
        while i + j <= b:
            if (i != 0 or j != 0) and _lose(a - i, b - j):
                return "WIN " + str(i) + " " + str(j)
            j += 1
    return "LOSE"
