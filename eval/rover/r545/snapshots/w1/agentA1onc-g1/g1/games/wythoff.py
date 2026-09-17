"""Wythoff's game: last player to take a stone wins.

Input (complete stdin text)::

    a b

A move is either (i) remove any positive number of stones from one pile, or
(ii) remove the same positive number from both piles.

Output: ``LOSE`` for losing positions, otherwise ``WIN i j`` where (i, j) is
the lexicographically smallest winning move (compare i first, then j; i, j >= 0
and not both zero).
"""

# Beatty sequences: the losing positions are (floor(n*phi), floor(n*phi^2))
# with phi = (1 + sqrt(5)) / 2.  Computed with exact integer arithmetic so no
# floating point rounding can leak into the decision.
_PHI_NUM, _PHI_DEN = 1, 1  # placeholder, replaced below


def _losing_set(limit: int):
    """Return the set of losing positions (unordered) with both coords <= limit.

    Uses the exact integer criterion: a position (a, b) with a <= b is losing
    iff a == floor(d * b) where d = (sqrt(5) - 1) / 2 satisfies
    d^2 + d == 1.  We instead build the pairs iteratively via the smallest
    unused value (Beatty construction) to stay purely integral.
    """
    pairs = []
    used = set()
    n = 0
    while True:
        n += 1
        # nth losing pair via integer square root: a_n = floor(n * phi).
        # floor(n*phi) = floor((n + floor(n*sqrt(5))) / 2) is *not* exact in
        # general, so use the integer recurrence based on isqrt of 5*n^2.
        phi_n = (n + _isqrt(5 * n * n)) // 2
        a = phi_n
        b = a + n
        if a > limit or b > limit:
            break
        if a in used or b in used:
            continue
        used.add(a)
        used.add(b)
        pairs.append((a, b))
    return pairs, used


def _isqrt(v: int) -> int:
    """Exact integer square root (floor) via Newton iteration."""
    if v < 0:
        raise ValueError("negative")
    if v < 2:
        return v
    x = 1 << ((v.bit_length() + 1) // 2)
    while True:
        y = (x + v // x) // 2
        if y >= x:
            return x
        x = y


def _is_losing(a: int, b: int) -> bool:
    """Exact test for a Wythoff losing position (a, b)."""
    x, y = (a, b) if a <= b else (b, a)
    n = y - x  # pair index difference
    # Losing pairs: (floor(n*phi), floor(n*phi) + n).
    if n <= 0:
        # (0,0) is losing, but inputs are >= 1; equal piles -> x == y == 0 only.
        return x == 0 and y == 0
    phi_n = (n + _isqrt(5 * n * n)) // 2
    return x == phi_n


def solve(text: str) -> str:
    """Return LOSE or the lexicographically smallest winning move."""
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])

    if _is_losing(a, b):
        return "LOSE"

    # Enumerate candidate moves in increasing i then j; first winning one wins.
    for i in range(0, a + 1):
        if i == 0:
            # Only one pile changes: take j from pile 2 (j >= 1).
            for j in range(1, b + 1):
                if _is_losing(a - i, b - j):
                    return "WIN {} {}".format(i, j)
        else:
            # Same-from-both move only (the other candidate, taking from pile 2
            # alone, has i == 0 and is covered above).
            if i <= b and _is_losing(a - i, b - i):
                return "WIN {} {}".format(i, i)
    return "LOSE"  # unreachable for a non-losing position
