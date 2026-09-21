"""Subtraction game."""


def solve(text: str) -> str:
    parts = text.split()
    n = int(parts[0])
    k = int(parts[1])
    moves = [int(x) for x in parts[2:2 + k]]
    moves = sorted(set(m for m in moves if m <= n))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m > i:
                break
            if not win[i - m]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
