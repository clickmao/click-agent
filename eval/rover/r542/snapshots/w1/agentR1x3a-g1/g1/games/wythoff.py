def _is_losing(a, b):
    seen = set()
    x = 0
    while True:
        p = (x * (1 + 5 ** 0.5) // 2)
        p = int(x * (1 + 5 ** 0.5) / 2)
        q = p + x
        seen.add((p, q))
        if p > 25 and q > 25:
            break
        x += 1
    lo, hi = min(a, b), max(a, b)
    for (p, q) in seen:
        if p == lo and q == hi:
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split())
    seen = set()
    x = 0
    while x <= 40:
        p = int(x * (1 + 5 ** 0.5) / 2)
        q = p + x
        seen.add((p, q))
        x += 1
    for (p, q) in seen:
        if (p == a and q == b) or (p == b and q == a):
            return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(a + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            los = False
            for (p, q) in seen:
                if (p == na and q == nb) or (p == nb and q == na):
                    los = True
                    break
            if los:
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return 'WIN ' + str(i) + ' ' + str(j)
