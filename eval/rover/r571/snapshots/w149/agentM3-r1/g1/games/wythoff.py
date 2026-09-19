from math import isqrt


LOSE_SET = set()
for _n in range(0, 40):
    _a = _n * (1 + isqrt(5)) // 2
    _b = _a + _n
    if _a <= 25 and _b <= 25:
        LOSE_SET.add((_a, _b))
    if _b <= 25:
        LOSE_SET.add((_b, _a))


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    return (a, b) in LOSE_SET


def _moves(a, b):
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > a or j > b:
                continue
            yield i, j


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_lose(a, b):
        return 'LOSE'
    for i, j in _moves(a, b):
        if _is_lose(a - i, b - j):
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
