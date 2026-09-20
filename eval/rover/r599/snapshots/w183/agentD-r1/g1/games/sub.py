"""Subtraction game: WIN m or LOSE for the first player."""


def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted({int(t) for t in tokens[2:2 + k]})
    moves = [s for s in moves if s >= 1]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
