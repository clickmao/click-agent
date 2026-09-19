"""Subtraction game: first-player win/lose with smallest winning first move."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(t) for t in tokens[2:2 + k])

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for take in moves:
            if take > stones:
                break
            if not win[stones - take]:
                win[stones] = True
                break

    if not win[n]:
        return 'LOSE'
    for take in moves:
        if take <= n and not win[n - take]:
            return 'WIN %d' % take
    return 'LOSE'
