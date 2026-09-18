"""Wythoff 博弈: 必败点判定, 否则给出字典序最小的必胜着法。"""


def cold(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    return lo == int((hi - lo) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if cold(a, b):
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            rem_a, rem_b = a - i, b - j
            if (i == 0 or j == 0 or i == j) and cold(rem_a, rem_b):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
