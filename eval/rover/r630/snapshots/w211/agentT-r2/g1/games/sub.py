"""Subtraction game: one heap, allowed moves, last stone wins (normal play)."""


def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
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
            return 'WIN ' + str(s)
    return 'LOSE'
