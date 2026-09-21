def solve(text):
    lines = text.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()
    a, b = map(int, lines[0].split()[:2])

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        for i in range(0, 26):
            j = (int(i * (1 + 5 ** 0.5) / 2) + i)
            if (i, j) == (x, y):
                return True
        return False

    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
