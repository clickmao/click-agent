def solve(text: str) -> str:
    lines = text.splitlines()
    a, b = (int(x) for x in lines[0].split())
    los = set()
    n = 0
    while n <= 25:
        x = int(n * ((1 + 5 ** 0.5) / 2) + 1e-9)
        y = x + n
        los.add((x, y))
        los.add((y, x))
        n += 1
    if (a, b) in los:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in los:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
