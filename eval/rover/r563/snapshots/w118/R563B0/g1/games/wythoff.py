def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    los = set()
    x, y = 0, 0
    while x <= 60:
        los.add((x, y))
        los.add((y, x))
        x, y = y + 1, x + y + 2
    if (a, b) in los:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0 and i == j and i > b):
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            if i > a or j > b:
                continue
            if (a - i, b - j) in los:
                best = (i, j)
                return 'WIN %d %d' % (i, j)
    if best is None:
        return 'WIN 0 0'
    return 'WIN %d %d' % best
