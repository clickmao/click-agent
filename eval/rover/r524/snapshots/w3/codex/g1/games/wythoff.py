from math import isqrt


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    n = b - a
    return a == (n + isqrt(5 * n * n)) // 2


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _losing(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _losing(a - i, b - j) and best is None:
                best = (i, j)
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
