"""Multi-pile Nim: report the winning move (smallest pile, its take).

Input format (complete stdin text)::

    m
    a1 a2 ... am

Each move removes any positive number of stones from exactly one pile; the
player taking the last stone wins.

Output: ``WIN p r`` with ``p`` the smallest 1-based index of a pile that has
a winning move and ``r`` the number of stones taken from it (each pile has at
most one winning take), or ``LOSE`` if the first player is losing.
"""

from __future__ import annotations


def solve(text: str) -> str:
    """Return the first player's optimal outcome for multi-pile Nim."""
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1 : 1 + m]]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"

    for idx, a in enumerate(piles, start=1):
        target = a ^ xor          # desired new size of this pile
        take = a - target         # positive because target < a here
        if take > 0:
            return f"WIN {idx} {take}"

    return "LOSE"  # unreachable: nonzero xor guarantees such a pile exists
