from math import isqrt


def _beatty(n: int) -> int:
    return (n + isqrt(5 * n * n)) // 2


def _losing(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    for k in range(0, y - x + 2):
        if y == x + k and x == _beatty(k):
            return True
    return False


def solve(text: str) -> str:
    data = text.split()
    if not data:
        return ""
    a, b = int(data[0]), int(data[1])
    if _losing(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
