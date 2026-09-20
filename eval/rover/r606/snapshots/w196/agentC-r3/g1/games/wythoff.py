def solve(text):
    a, b = map(int, text.split())
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            x, y = a - i, b - j
            moves.append((i, j, x, y))
    moves.sort(key=lambda t: (t[0], t[1]))
    for i, j, x, y in moves:
        if (x, y) in COLD:
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def _cold():
    s = set()
    used = set()
    for n in range(0, 26):
        x = (n * (1 + 5 ** 0.5)) / 2
        a = int(x)
        while a in used or (a + n) in used or a < 0:
            a += 1
        used.add(a)
        used.add(a + n)
        s.add((a, a + n))
        s.add((a + n, a))
    return s


COLD = _cold()
