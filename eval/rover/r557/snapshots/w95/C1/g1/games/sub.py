"""Subtraction game: determine win/lose and the smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    n, k = int(tokens[0]), int(tokens[1])
    moves = [int(t) for t in tokens[2:2 + k]]
    moves.sort()

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
