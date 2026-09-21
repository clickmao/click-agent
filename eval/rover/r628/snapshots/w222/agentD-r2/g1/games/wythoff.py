def _cold(a, b):
    fa = int(a * 0.6180339887498949) + 1
    for n in range(max(0, fa - 3), fa + 4):
        if (a, b) == (n + int(n * 0.6180339887498949) + 1,
                      n + int(n * 0.6180339887498949) + 2):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return 'WIN %d %d' % (i, j)
