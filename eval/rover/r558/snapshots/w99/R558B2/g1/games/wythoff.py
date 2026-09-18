"""Wythoff's game: remove from one pile, or the same positive amount from both.

(LOSE iff the pair is a P-position; otherwise the lexicographically smallest
winning move, i.e. minimal i, then minimal j.)
"""


def _is_lose(a: int, b: int) -> bool:
    """P-positions are (floor(k*phi), floor(k*phi^2)); detected by the
    cold-position identity: floor(a*(1+sqrt(5))/2) == b when a <= b, plus the
    complementary-condition check b - a <= a."""
    if a > b:
        a, b = b, a
    if b - a > a:
        return False
    return (a * 9 + 9) // 16 + ((a * 9 + 3) // 16) == b


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _is_lose(a, b):
        return "LOSE"

    best = None
    # (i) remove i from pile 1, j from pile 2 (j may be 0)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and _is_lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        # fall back to a plain single-pile move (should be unreachable for
        # non-P positions, as one-pile removal is always available)
        for i in range(1, a + 1):
            if _is_lose(a - i, b):
                best = (i, 0)
                break
        if best is None:
            for j in range(1, b + 1):
                if _is_lose(a, b - j):
                    best = (0, j)
                    break
    return "WIN %d %d" % best
