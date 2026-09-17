"""Subtraction game: last move wins. Determine first player's outcome."""


def solve(text: str) -> str:
    """Read 'n k' then k distinct allowed takes.

    Return 'WIN m' with the smallest winning first take, or 'LOSE'.
    """
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split()[:k])

    # win[i] = True iff position with i stones is a win for the player to move
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(m <= i and not win[i - m] for m in moves)

    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
