"""Subtraction game: Win/Lose plus smallest winning move."""


def solve(text: str) -> str:
    lines = text.split()
    it = iter(lines)
    n = int(next(it))
    k = int(next(it))
    steps = [int(next(it)) for _ in range(k)]
    steps = sorted(set(steps))
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
