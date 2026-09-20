"""Subtraction game: first player wins/loses and the smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    n, k = int(tokens[0]), int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    # win[i] == True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
