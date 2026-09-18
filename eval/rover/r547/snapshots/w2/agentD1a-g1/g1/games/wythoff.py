def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())
    import math
    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        tx = int(math.floor(d * (1 + math.sqrt(5)) / 2))
        return x == tx and y == x + d
    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
