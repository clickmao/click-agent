from math import isqrt


def _win(a: int, b: int):
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                if not _lose(a - i, b - j):
                    return (i, j)
            elif i > 0 and j == 0:
                if not _lose(a - i, b):
                    return (i, j)
            elif i == 0 and j > 0:
                if not _lose(a, b - j):
                    return (i, j)
    return None


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    n = b - a
    return a == (n * (1 + isqrt(5)) // 2 - n + n)
