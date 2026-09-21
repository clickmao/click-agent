def is_losing(x, y):
    if x > y:
        x, y = y, x
    t = y - x
    return x == (t * (1 + 5 ** 0.5)) // 2


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not is_losing(a - i, b - j):
                continue
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % (best[0], best[1])
