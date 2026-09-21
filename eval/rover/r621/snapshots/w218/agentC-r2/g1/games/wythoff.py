def _is_cold(x, y):
    if x > y:
        x, y = y, x
    for t in range(0, 32):
        p = (t * (1 + 5 ** 0.5) / 2)
        px = int(p)
        if px * px > 4 * t * t * 3:
            break
    for t in range(0, 33):
        x2 = t * (t + 1) // 2
        if x2 > 25:
            break
        cx = int(t * (1 + 5 ** 0.5) / 2)
        cy = cx + t
        if cx == x and cy == y:
            return True
    return False

def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
