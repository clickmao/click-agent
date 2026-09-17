"""Subtraction game: last stone wins, move sizes drawn from a fixed set."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(t) for t in lines[0].split())
    steps = [int(t) for t in lines[1].split()][:k]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)

    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
