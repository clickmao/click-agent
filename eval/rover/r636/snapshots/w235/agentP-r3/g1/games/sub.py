"""Subtraction game: WIN m (smallest winning take) or LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = sorted(set(map(int, lines[1].split())))
    win = [False] * (n + 1)
    first = [0] * (n + 1)
    for t in range(1, n + 1):
        for s in steps:
            if s <= t and not win[t - s]:
                win[t] = True
                first[t] = s
                break
    if win[n]:
        return "WIN " + str(first[n])
    return "LOSE"
