def _losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    t = int(((5 ** 0.5 + 1) / 2) * (y - x))
    for base in (t - 2, t - 1, t, t + 1, t + 2):
        if base < 0:
            continue
        if x == int(base * (1 + 5 ** 0.5) / 2) and y == base + int(base * (1 + 5 ** 0.5) / 2):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            if _losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
