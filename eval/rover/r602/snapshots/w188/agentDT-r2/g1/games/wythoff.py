def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        if x == 0 and y == 0:
            return True
        d = y - x
        if d == 0:
            return False
        tx = int(d * 1.618033988749895)
        for cand in (tx - 1, tx, tx + 1, tx + 2):
            if cand >= 0 and cand + d == y and cand == x:
                return True
        return False

    if losing(a, b):
        return 'LOSE'

    cands = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if losing(a - i, b - j):
                    cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN ' + str(i) + ' ' + str(j)
