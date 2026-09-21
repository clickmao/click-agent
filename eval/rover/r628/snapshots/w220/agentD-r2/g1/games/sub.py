"""Subtraction game: WIN m (smallest winning first move) or LOSE."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    while lines and lines[-1].strip() == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    # win[i] = True if the player to move with i stones can force a win
    win = [False] * (n + 1)
    move = [0] * (n + 1)
    for i in range(1, n + 1):
        best = None
        for s in steps:
            if s <= i and not win[i - s]:
                if best is None or s < best:
                    best = s
        if best is not None:
            win[i] = True
            move[i] = best
    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % move[n]
