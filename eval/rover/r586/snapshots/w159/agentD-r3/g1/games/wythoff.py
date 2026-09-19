def solve(text):
    a, b = (int(x) for x in text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * 1.618033988749895 / 1.618033988749895 * 0 + d * 0.618033988749895)

    def cold(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        xr = (d * 1000003) // 1618033
        for c in range(max(0, xr - 2), xr + 3):
            if c >= 0 and int(c * 1.618033988749895) == c + d and c + d >= 0:
                if c == x:
                    return True
        d2 = x + y
        return False

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        c = (d * 1618033) // 1000000
        for t in range(max(0, c - 2), c + 3):
            if int(t * 1.618033988749895) == t + d and t == x:
                return True
        return False

    if is_losing(a, b):
        return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        j = a + b - i - (b - i)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i == 0 and j == 0:
                continue
            if i > a or j > b:
                continue
            ni, nj = a - i, b - j
            if ni < 0 or nj < 0:
                continue
            if is_losing(ni, nj):
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN %d %d' % (i, j)
