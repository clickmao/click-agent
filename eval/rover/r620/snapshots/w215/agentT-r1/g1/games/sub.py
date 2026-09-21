"""Subtraction game: first-player win/lose and smallest winning take."""


def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    steps = []
    for _ in range(k):
        steps.append(int(tokens[pos])); pos += 1

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w

    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
