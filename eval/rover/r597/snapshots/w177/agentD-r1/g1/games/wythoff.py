def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        i = y - x
        px = (i * (1 + 5 ** 0.5)) / 2.0
        return x == int(px)

    if losing(a, b):
        return 'LOSE'

    cands = set()
    for i in range(0, a + 1):
        if losing(a - i, b):
            cands.add((i, 0))
    for j in range(0, b + 1):
        if losing(a, b - j):
            cands.add((0, j))
    for t in range(1, min(a, b) + 1):
        if losing(a - t, b - t):
            cands.add((t, t))
    cands.discard((0, 0))
    i, j = min(cands)
    return 'WIN ' + str(i) + ' ' + str(j)
