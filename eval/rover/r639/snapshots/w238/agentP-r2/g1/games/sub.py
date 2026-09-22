"""Subtraction game: take exactly one of the allowed amounts; last stone wins."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    # win[p] = True if the player to move with p stones has a winning strategy
    win = [False] * (n + 1)
    for p in range(1, n + 1):
        win[p] = any(m <= p and not win[p - m] for m in moves)
    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
