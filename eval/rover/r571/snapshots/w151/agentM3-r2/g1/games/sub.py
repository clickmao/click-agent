"""Subtraction game: report WIN m (smallest winning first move) or LOSE."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(x) for x in tokens[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN ' + str(best)
