"""Subtraction game: decide first-player win/lose and smallest winning move."""


def solve(text):
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()]
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
