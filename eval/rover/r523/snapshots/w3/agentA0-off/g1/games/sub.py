"""Subtraction game: outcome of the first player, smallest winning move."""


def solve(text: str) -> str:
    parts = text.split()
    n, k = int(parts[0]), int(parts[1])
    moves = sorted(int(x) for x in parts[2:2 + k])

    # win[i] = True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
