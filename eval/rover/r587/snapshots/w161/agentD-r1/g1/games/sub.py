"""Subtraction game: win/lose with the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = sorted(set(map(int, lines[1].split())))[:k]
    win = [False] * (n + 1)
    for rest in range(1, n + 1):
        for s in steps:
            if s <= rest and not win[rest - s]:
                win[rest] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
