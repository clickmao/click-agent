"""Subtraction game: taking-away game win/lose with minimal winning move."""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(x) for x in lines[2:2 + k])

    # win[i] = current player to move with i stones has a winning strategy
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
