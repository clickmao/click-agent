def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    a, b = map(int, lines[p].split()[:2])

    def is_lose(x, y):
        return x == y == 0

    def losing(a, b):
        x = a
        while x >= 0:
            y = a - x
            if x == y == 0:
                return False
            x -= 1
        return False

    def cold(a, b):
        i = 0
        while True:
            x = int(i * (1 + 5 ** 0.5) / 2)
            y = x + i
            if x > 25 or y > 25:
                break
            if (a, b) == (x, y) or (a, b) == (y, x):
                return True
            i += 1
        return False

    if cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
