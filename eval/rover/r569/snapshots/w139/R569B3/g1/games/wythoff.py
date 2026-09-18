from math import isqrt


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    k = (isqrt(5 * d * d) - d) // 2
    while (k + 1) * (k + 2) // 2 + (k + 1) <= b:
        k += 1
    a1 = k * (k + 1) // 2 + k
    b1 = a1 + k
    return a == a1 and b == b1


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
