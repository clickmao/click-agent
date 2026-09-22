def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        n = (d * 1000000) // 1618033
        for cand in (n - 2, n - 1, n, n + 1, n + 2):
            if cand < 0:
                continue
            if (cand * 1618033) // 1000000 == x and (cand * 2618033) // 1000000 == y:
                return True
        return False

    if losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
