"""Take-away subtraction game: n k then k allowed move sizes."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if len(lines) >= 1 and lines[-1] == '':
        lines = lines[:-1]
    n, k = (int(x) for x in lines[0].split())
    sizes = [int(x) for x in lines[1].split()]
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        ok = False
        for s in sizes:
            if s <= m and not win[m - s]:
                ok = True
                break
        win[m] = ok
    if not win[n]:
        return 'LOSE'
    best = None
    for s in sizes:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN ' + str(best)
