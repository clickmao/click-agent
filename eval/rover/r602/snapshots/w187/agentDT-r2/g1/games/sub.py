"""Subtraction game: first player's win value."""


def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    steps = sorted(set(int(tokens[pos + i]) for i in range(k)))
    steps = [s for s in steps if s <= 12 and s >= 1]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in steps:
            if s <= n and not win[n - s]:
                return 'WIN %d' % s
    return 'LOSE'
