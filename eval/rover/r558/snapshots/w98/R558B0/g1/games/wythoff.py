def _cold(a, b):
    if a > b:
        a, b = b, a
    for n in range(0, 26):
        p = (n * (1 + 5 ** 0.5)) / 2.0
        an = int(p + 1e-9)
        b1 = an + n
        b2 = an + n + 1
        if (a == an and b == b1) or (a == an and b == b2):
            return True
    return False


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0) and i != j:
                continue
            if _cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
