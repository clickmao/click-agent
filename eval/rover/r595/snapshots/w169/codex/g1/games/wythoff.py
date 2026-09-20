"""Wythoff's game: losing-position test and the lexicographically smallest winning move.

A move is a pair (i, j) with i, j >= 0 (not both zero) that is legal when either
i == 0 (take from pile 2), j == 0 (take from pile 1) or i == j (take from both).
Moves are compared by (i, j) lexicographically, so i == 0 moves come first.
"""

LIMIT = 25


def _build() -> set:
    """All losing positions (a, b) with 0 <= a, b <= LIMIT."""
    losing = set()
    for total in range(0, 2 * LIMIT + 1):
        for a in range(0, min(total, LIMIT) + 1):
            b = total - a
            if b > LIMIT:
                continue
            win = False
            for i in range(1, a + 1):
                if (a - i, b) in losing:
                    win = True
                    break
            if not win:
                for j in range(1, b + 1):
                    if (a, b - j) in losing:
                        win = True
                        break
            if not win:
                for i in range(1, min(a, b) + 1):
                    if (a - i, b - i) in losing:
                        win = True
                        break
            if not win:
                losing.add((a, b))
    return losing


_LOSING = _build()


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    if (a, b) in _LOSING:
        return "LOSE"

    # i == 0 has the smallest first component; among those pick the smallest j.
    for j in range(1, b + 1):
        if (a, b - j) in _LOSING:
            return "WIN 0 %d" % j
    # Then remaining single-pile moves from pile 1 and equal-pair moves, in (i, j) order.
    for i in range(1, a + 1):
        if (a - i, b) in _LOSING:
            return "WIN %d 0" % i
        if i <= b and (a - i, b - i) in _LOSING:
            return "WIN %d %d" % (i, i)
    return "LOSE"
