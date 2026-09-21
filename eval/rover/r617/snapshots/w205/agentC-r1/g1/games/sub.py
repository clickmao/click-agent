"""Subtraction game: determine win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()]
    moves = sorted(set(m for m in moves if 1 <= m <= n))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m <= i and not win[i - m]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
