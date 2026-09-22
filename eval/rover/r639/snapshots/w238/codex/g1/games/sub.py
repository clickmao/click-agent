"""Subtraction game: report the smallest winning first move or ``LOSE``."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(x) for x in tokens[2:2 + k]]
    moves.sort()

    win = [False] * (n + 1)
    for remaining in range(1, n + 1):
        for take in moves:
            if take <= remaining and not win[remaining - take]:
                win[remaining] = True
                break

    if not win[n]:
        return 'LOSE'
    for take in moves:
        if take <= n and not win[n - take]:
            return 'WIN {}'.format(take)
    return 'LOSE'
