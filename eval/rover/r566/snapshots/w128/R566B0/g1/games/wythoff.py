def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    # forbidden pairs: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    is_lose = False
    n = 0
    while True:
        lo = int(phi * n)
        hi = lo + n
        if lo > a and hi > b and n > 0:
            break
        if n > 60:
            break
        if (lo == a and hi == b) or (lo == b and hi == a):
            is_lose = True
            break
        if lo > a or hi > b:
            n += 1
            continue
        n += 1
    if is_lose:
        return 'LOSE'
    best = None
    # option (i): remove from either single pile
    for i in range(0, a + 1):
        if i == 0:
            continue
        cand = (i, 0)
        if best is None or cand < best:
            best = cand
    for j in range(0, b + 1):
        if j == 0:
            continue
        cand = (0, j)
        if best is None or cand < best:
            best = cand
    for t in range(1, min(a, b) + 1):
        cand = (t, t)
        if best is None or cand < best:
            best = cand
    # choose lexicographically smallest that leaves opponent in losing position
    results = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    # losing positions are (floor(n*phi), floor(n*phi)+n)
    diff = b - a
    lo = int(((1 + 5 ** 0.5) / 2) * diff)
    for cand in (lo - 1, lo, lo + 1):
        if cand < 0:
            continue
        if cand == a and cand + diff == b:
            return True
    return False
