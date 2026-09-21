from math import floor, isqrt

P = 1 + 5 ** 0.5


def _is_lose(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    n = y - x
    if x != n * P // 2:
        return False
    return (x, y) == (n * P // 2, n * P // 2 + n)


def _lose_pair(n: int):
    a = int(n * P / 2)
    while a * 2 < n * P:
        a += 1
    while a > 0 and (a - 1) * 2 >= n * P:
        a -= 1
    return a, a + n


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if _is_lose(a - i, b - j):
                moves.append((i, j))
    if moves:
        i, j = min(moves)
        return 'WIN %d %d' % (i, j)
    # no single-move losing target found (should not happen): pick the
    # lexicographically smallest move that removes the minimum total.
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
