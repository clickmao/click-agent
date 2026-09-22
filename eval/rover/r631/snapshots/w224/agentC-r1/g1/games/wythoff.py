def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    def is_losing(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        for t in range(0, 30):
            p = (1 + 5 ** 0.5) / 2
            c = int(t * p + 1e-9)
            d = c + t
            if c > 25 or d > 25:
                break
            if c == lo and d == hi:
                return True
            if c > hi:
                break
        return False

    if is_losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                continue
            if is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
