"""Subtraction game: first player's optimal opening move."""


def solve(text):
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()]
    moves.sort()
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        ok = False
        for s in moves:
            if s <= i and not win[i - s]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
