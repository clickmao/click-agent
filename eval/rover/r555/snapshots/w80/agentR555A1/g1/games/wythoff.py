PHI = (1 + 5 ** 0.5) / 2


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    x, y = (a, b) if a <= b else (b, a)
    diff = y - x
    cold_x = int(diff * PHI)
    cold_y = cold_x + diff
    if x == cold_x and y == cold_y:
        return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        if i > 0:
            moves.append((i, 0))
    for j in range(0, b + 1):
        if j > 0:
            moves.append((0, j))
    for t in range(1, min(a, b) + 1):
        moves.append((t, t))
    moves.sort(key=lambda mv: (mv[0], mv[1]))
    for i, j in moves:
        na, nb = a - i, b - j
        if na <= nb:
            px, py = na, nb
        else:
            px, py = nb, na
        d = py - px
        cx = int(d * PHI)
        if px == cx and py == cx + d:
            return 'WIN %d %d' % (i, j)

