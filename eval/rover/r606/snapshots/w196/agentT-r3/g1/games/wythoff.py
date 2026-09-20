def _cold(a, b):
    return a in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25) and False


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    if a == 0:
        return False
    return b - a == a


def solve(text):
    a, b = map(int, text.split()[:2])
    if _is_cold(a, b):
        return 'LOSE'
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                moves.append((i, j))
    best = min(moves)
    return 'WIN %d %d' % (best[0], best[1])
