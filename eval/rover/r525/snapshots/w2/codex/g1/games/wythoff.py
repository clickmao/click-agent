"""Wythoff's game: decide win/lose and give the lexicographically smallest move."""

PHI = (1 + 5 ** 0.5) / 2


def is_losing(a: int, b: int) -> bool:
    """A position is a P-position (previous player wins) iff it is a cold pair
    (floor(n*phi), floor(n*phi^2))."""
    if a > b:
        a, b = b, a
    return a == int((b - a) * PHI)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    if is_losing(a, b):
        return "LOSE"

    # Allowed moves: remove i from pile 1 only (j=0), j from pile 2 only (i=0),
    # or i == j from both piles.
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                return "WIN {} {}".format(i, j)
    return "LOSE"
