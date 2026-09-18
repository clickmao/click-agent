"""Subtraction game: smallest winning first move or LOSE."""


def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(t) for t in tokens[2:2 + k]]
    win = [False] * (n + 1)
    for rem in range(1, n + 1):
        for s in steps:
            if s <= rem and not win[rem - s]:
                win[rem] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
