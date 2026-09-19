def solve(text):
    a, b = map(int, text.split()[:2])
    moves = []
    if b:
        moves.append((0, b))
    for i in range(1, a + 1):
        moves.append((i, 0))
        if i <= b:
            moves.append((i, i))
    for i, j in sorted(moves):
        x, y = a - i, b - j
        if x > y:
            x, y = y, x
        ok = True
        prev = []
        for t in range(0, y + 1):
            cand = (t + (y - x), t) if y - x >= 0 else None
            if cand and cand[1] <= y and cand[0] <= y and cand[1] <= t and cand[0] - cand[1] == y - x:
                pass
        for x0 in range(0, y + 1):
            cand = (x0 + (y - x), x0) if y - x >= 0 else None
            if cand and cand == (x, y):
                ok = False
                break
        if ok and (x, y) != (0, 0):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
