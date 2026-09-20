def _grundy(a, b):
    d = a - b
    if d < 0:
        d = -d
    # Beatty: losing iff min/floor(min*phi) == (a,b)
    import math
    phi = (1 + math.sqrt(5)) / 2
    lo = min(a, b)
    other = int(math.floor(lo * phi))
    return lo == (int(math.floor(other / phi))) and max(a, b) == other


def _is_losing(a, b):
    b, a = min(a, b), max(a, b)
    k = a - b
    beat = int(k * (1 + 5 ** 0.5) / 2)
    return b == beat


def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            # legal move: remove from one pile only, or same count from both
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if _is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)

    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
