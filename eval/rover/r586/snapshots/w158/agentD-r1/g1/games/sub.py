"""Subtraction game: first player win/lose and smallest winning first move."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    win = [False] * (n + 1)
    for target in range(1, n + 1):
        for s in steps:
            if s > target:
                break
            if not win[target - s]:
                win[target] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
