"""Wythoff 博弈: 输出字典序最小的必胜着法（WIN i j）或 LOSE。"""


def _lose(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2 + 1e-9)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _lose(a - i, b - j):
                moves.append((i, j))
    if not moves:
        return 'LOSE'
    i, j = min(moves)
    return 'WIN %d %d' % (i, j)
