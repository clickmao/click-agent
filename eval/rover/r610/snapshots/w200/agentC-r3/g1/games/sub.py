"""Subtraction game: first player's winning move, smallest take."""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = sorted(int(x) for x in lines[2:2 + k])
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(m <= x and not win[x - m] for m in moves)
    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
