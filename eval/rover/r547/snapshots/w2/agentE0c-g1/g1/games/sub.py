"""Subtraction game: win/lose + smallest winning first move."""


def solve(text: str) -> str:
    parts = text.split()
    n, k = int(parts[0]), int(parts[1])
    moves = sorted(int(x) for x in parts[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
