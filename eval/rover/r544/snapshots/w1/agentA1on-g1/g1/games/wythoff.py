"""Wythoff's game: report a losing point, or the lexicographically smallest win.

Input format (complete stdin text)::

    a b

Two piles of ``a`` and ``b`` stones.  A move is either (i) remove any positive
number from one pile, or (ii) remove the same positive number from both piles;
the player taking the last stone wins.

Output: ``LOSE`` when the position is losing for the mover, otherwise
``WIN i j`` where ``(i, j)`` is the lexicographically smallest winning move
(compare ``i`` first, then ``j``; ``i, j >= 0`` and not both zero).
"""

from __future__ import annotations

_MAX = 25  # spec bound for a and b


def _cold_positions(limit: int) -> set[tuple[int, int]]:
    """Return Wythoff cold (P-)positions ``(lo, hi)`` with ``hi <= limit``.

    Cold positions are the Beatty pair ``(floor(n * phi), floor(n * phi^2))``
    for ``n >= 1``; they are exactly the pairs losing for the player to move.
    They are built here by the mex rule (each new pair uses the two smallest
    integers not used by any earlier pair), which is self-contained and does
    not rely on floating-point ``phi`` rounding.
    """
    cold: set[tuple[int, int]] = set()
    used: set[int] = set()
    lo = 1
    while True:
        while lo in used:
            lo += 1
        hi = lo + 1
        while hi in used:
            hi += 1
        if hi > limit:
            break
        cold.add((lo, hi))
        used.add(lo)
        used.add(hi)
        lo += 1
    return cold


_COLD: set[tuple[int, int]] = _cold_positions(_MAX)


def _is_cold(a: int, b: int) -> bool:
    """True when ``(a, b)`` is a losing position for the player to move."""
    if a > b:
        a, b = b, a
    return (a, b) in _COLD


def solve(text: str) -> str:
    """Return the first player's optimal outcome for Wythoff's game."""
    a, b = (int(x) for x in text.split()[:2])
    if _is_cold(a, b):
        return "LOSE"

    lo, hi = (a, b) if a <= b else (b, a)
    for i in range(lo + 1):
        for j in range(hi + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # only one-pile or equal-two-pile removals are legal
            if _is_cold(lo - i, hi - j):
                return f"WIN {i} {j}"
    raise AssertionError("winning position has no winning move")
