"""Subtraction game: report the smallest winning first move, or LOSE."""


def solve(text: str) -> str:
    data = text.split()
    n, k = int(data[0]), int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])

    # win[x] is True if the player to move with x stones can force a win.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"

    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s

    return "LOSE"
