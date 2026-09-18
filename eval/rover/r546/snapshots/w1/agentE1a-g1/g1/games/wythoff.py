"""Wythoff 博弈必败点判定。"""

from math import isqrt


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == int((b - a) * (1 + 5 ** 0.5) / 2):
        return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _lose(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
