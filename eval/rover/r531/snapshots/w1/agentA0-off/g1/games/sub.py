"""Subtraction game: WIN/LOSE and the smallest winning first move.

stdin format:
    line 1: n k        (1<=n<=80 stones, 1<=k<=12 number of allowed moves)
    line 2: k distinct integers s1..sk (1<=si<=12, 1 is guaranteed present)
play:
    two players alternate removing exactly one of the allowed amounts;
    taking the last stone wins.
stdout:
    "WIN m"  with m the numerically smallest winning first move, or
    "LOSE"   when the first player loses with optimal play.
"""

__all__ = ["solve"]


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    # P[i] is True when the player to move with i stones LOSES (P-position).
    # i = 0 is a loss for the player to move (previous player took last stone).
    P = [False] * (n + 1)
    P[0] = True
    for i in range(1, n + 1):
        # Winning iff SOME legal move reaches a losing position.
        P[i] = not any(P[i - s] for s in steps if s <= i)

    if P[n]:
        return "LOSE"
    for s in steps:  # ascending => numerically smallest winning first move
        if s <= n and P[n - s]:
            return "WIN %d" % s
    return "LOSE"  # unreachable
