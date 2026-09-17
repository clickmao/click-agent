"""Subtraction game: last stone wins; report the smallest winning first move."""


def solve(text: str) -> str:
    """text = full stdin; return 'WIN m' (smallest winning first take) or 'LOSE'."""
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = [int(x) for x in lines[2:2 + k]]

    # win[i] = True if the player to move with i stones has a winning strategy.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)

    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
