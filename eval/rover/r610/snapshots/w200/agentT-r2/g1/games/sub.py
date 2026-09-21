"""Subtraction game: first player win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(0 <= x - s and not win[x - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if 0 <= n - s and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
