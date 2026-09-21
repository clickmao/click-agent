def solve(text: str) -> str:
    def is_losing(a, b):
        if a > b:
            a, b = b, a
        d = b - a
        return a == int(d * (1 + 5 ** 0.5) / 2 + 1e-9)

    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
