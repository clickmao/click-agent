"""Subtraction game: WIN with lexicographically/smallest winning first move, else LOSE."""


def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    steps = [int(x) for x in lines[1].split()][:k]
    steps = sorted(set(steps))

    # win[x] = True iff the player to move with x stones can force a win.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in steps:
            if s <= x and not win[x - s]:
                w = True
                break
        win[x] = w

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
