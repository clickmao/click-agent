"""Subtraction game: normal play, last stone wins."""


def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(t) for t in tokens[2:2 + k])
    # win[x] = True if the player to move with x stones can force a win.
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
