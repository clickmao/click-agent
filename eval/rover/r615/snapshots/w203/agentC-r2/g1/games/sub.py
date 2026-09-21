"""Subtraction game: win/lose plus smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split()[:k])
    # win[x] = True if position with x stones is winning for player to move
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    # moves are sorted ascending, so best is the numerically smallest winning move
    return 'WIN %d' % best
