"""Wythoff's game: remove from one heap or equal amounts from both, last wins."""

from math import isqrt

_COLD = set()


def _build(limit: int = 60) -> None:
    for n in range(limit + 1):
        p = (isqrt(5 * n * n) + n) // 2
        q = p + n
        _COLD.add((p, q))
        _COLD.add((q, p))


_build()


def _is_cold(a: int, b: int) -> bool:
    return (a, b) in _COLD


def _moves(a: int, b: int):
    for i in range(a + 1):
        yield (i, 0)
    for j in range(1, b + 1):
        yield (0, j)
    for t in range(1, min(a, b) + 1):
        yield (t, t)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    if _is_cold(a, b):
        return "LOSE"

    best = None
    for i, j in _moves(a, b):
        if _is_cold(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
