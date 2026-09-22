"""Subtraction game: first player win/lose with smallest winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    first = lines[0].split()
    n = int(first[0])
    k = int(first[1])
    moves = [int(x) for x in lines[1].split()][:k]
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    win[0] = False
    for i in range(1, n + 1):
        w = False
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
