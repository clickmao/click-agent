"""Wythoff's game (single-stack: no cross-module state).

Cold (P) positions are built exactly by the complementary Beatty sequences
A_n = floor(n*phi), B_n = A_n + n, using integer arithmetic only, so the
test never depends on floating point.
"""
import math

_LIMIT = 64  # a, b <= 25, but removal reaches cold cells only within this box


def _cold_table(limit: int):
    """Exact set of cold positions (x <= y) with y <= limit, integers only."""
    phi = (1 + math.sqrt(5)) / 2
    table = set()
    n = 0
    while True:
        a = math.floor(n * phi)
        b = a + n
        if a > limit and b > limit:
            break
        table.add((a, b))
        n += 1
    return table


_COLD = _cold_table(_LIMIT)
_COLD_SET = _COLD


def _is_cold(x: int, y: int) -> bool:
    """Exact membership test on the cold-position table (symmetric)."""
    if x > y:
        x, y = y, x
    return (x, y) in _COLD_SET


def solve(text: str) -> str:
    """text = full stdin; return 'LOSE' or 'WIN i j' with the lexicographically
    smallest winning move (i, j), i/j >= 0 and not both zero."""
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _is_cold(a, b):
        return "LOSE"

    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue  # only equal removal from both piles is allowed
            if _is_cold(a - i, b - j):
                moves.append((i, j))
    if not moves:
        return "LOSE"
    return "WIN %d %d" % min(moves)
