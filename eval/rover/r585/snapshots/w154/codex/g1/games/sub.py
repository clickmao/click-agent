"""Subtraction game: a player takes exactly one of the allowed amounts."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(x) for x in tokens[2:2 + k])

    # win[i] = True if the player to move with i stones can force a win
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"

    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s

    return "LOSE"
