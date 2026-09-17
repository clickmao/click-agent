"""Subtraction game with a fixed set of allowed moves."""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])

    # win[i]: player to move with i stones remaining wins
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for take in moves:
            if take > stones:
                break
            if not win[stones - take]:
                win[stones] = True
                break

    if not win[n]:
        return "LOSE"
    for take in moves:
        if take <= n and not win[n - take]:
            return "WIN {}".format(take)
    return "LOSE"
