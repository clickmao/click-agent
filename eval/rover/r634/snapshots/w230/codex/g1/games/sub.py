"""Subtraction game: first player win/lose and smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]
    steps = sorted(set(steps))

    # win[i] = True if the player to move with i stones wins.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
