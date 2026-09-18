"""Wythoff 博弈：字典序最小的必胜着法 (i, j)。"""


def _losing(a, b):
    """(a, b) 是否为必败点（a <= b）。"""
    if a > b:
        a, b = b, a
    d = b - a
    ca = (5 ** 0.5 + 1) / 2
    x = int(d * ca)
    for cand in (x - 1, x, x + 1):
        if cand >= 0 and cand == a and cand + d == b:
            return True
    return False


def solve(text: str) -> str:
    """返回 LOSE 或 WIN i j。"""
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and _losing(a - i, b - j):
                if best is None:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
