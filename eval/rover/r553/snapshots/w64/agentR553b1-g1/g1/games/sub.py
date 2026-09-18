"""Subtraction game: the losing/winning position and the smallest winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    n, k = (int(t) for t in lines[0].split()[:2])
    moves = sorted(int(t) for t in lines[1].split()[:k])

    # win[x] = True iff the player to move with x stones wins.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for m in moves:
            if m > x:
                break
            if not win[x - m]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
