"""Subtraction game: players remove an allowed number of stones."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(v) for v in lines[0].split())
    moves = sorted(int(v) for v in lines[1].split()[:k])
    # win[x] = True if the player to move with x stones can force a win.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
