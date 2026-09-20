def solve(text):
    a, b = map(int, text.split()[:2])

    def losing(p, q):
        if p > q:
            p, q = q, p
        return p <= q and ((q - p) * 6180339887498949 // 10000000000000000 == p or
                           ((q - p) * 1618033988749895 // 1000000000000000 == p and False))

    def is_losing(p, q):
        if p > q:
            p, q = q, p
        d = q - p
        return (d * 10000000000000000) // 6180339887498949 == p

    if is_losing(a, b):
        return 'LOSE'

    moves = set()
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                moves.add((i, j))
    best = min(moves)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
