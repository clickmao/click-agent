"""Wythoff's game: moving-to-a-losing-position first move.

Input (complete stdin text):
    line 1: a b   (1..25 each)

Rules: remove any positive number from one pile, or the same positive number
from both piles; whoever takes the last stone wins.

Output:
    'LOSE' if the position is a first-player loss, else 'WIN i j' where
    (i, j) is the lexicographically smallest winning move (i, j >= 0,
    not both zero).
"""

import math
from typing import List, Set, Tuple


def _losing_positions(limit: int) -> Set[Tuple[int, int]]:
    """Unordered P-positions with both coordinates <= limit.

    The k-th P-position is (floor(k*phi), floor(k*phi^2)).  Using
    floor(k*phi) = floor((k + floor(sqrt(5*k^2)))/2) keeps it exact.
    """
    res: Set[Tuple[int, int]] = set()
    k = 0
    while True:
        k += 1
        s = math.isqrt(5 * k * k)
        if (k + s) % 2 != 0:
            s -= 1
        lo = (k + s) // 2      # floor(k*phi)
        hi = lo + k            # floor(k*phi^2)
        if lo > limit and hi > limit:
            break
        res.add((lo, hi))
        res.add((hi, lo))
    return res


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    losing = _losing_positions(max(a, b))

    candidates: List[Tuple[int, int]] = []
    # (i) remove from a single pile
    for i in range(0, a + 1):
        if i and (a - i, b) in losing:
            candidates.append((i, 0))
    for j in range(0, b + 1):
        if j and (a, b - j) in losing:
            candidates.append((0, j))
    # (ii) remove the same positive number from both piles
    for t in range(1, min(a, b) + 1):
        if (a - t, b - t) in losing:
            candidates.append((t, t))

    if not candidates:
        return "LOSE"
    i, j = min(candidates)
    return "WIN {} {}".format(i, j)
