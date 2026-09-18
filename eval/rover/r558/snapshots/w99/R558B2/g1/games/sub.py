"""Subtraction game: each move removes exactly one of the allowed counts; last stone wins."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted({int(t) for t in tokens[2:2 + k]})

    # win[i] = True if the player to move with i stones has a winning strategy
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"

    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
