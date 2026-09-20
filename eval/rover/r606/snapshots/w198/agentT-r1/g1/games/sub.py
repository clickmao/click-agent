"""Subtraction game: win/lose and the smallest winning move."""


def solve(text):
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split()[:2])
    moves = [int(x) for x in lines[1].split()[:k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    m = min(s for s in moves if s <= n and not win[n - s])
    return 'WIN %d' % m
