MAXN = 25


def build_losing():
    losing = set()
    used = set()
    p = 1
    while True:
        q = p + int(p * (5 ** 0.5 + 1) / 2)
        if q > MAXN:
            break
        losing.add((p, q))
        losing.add((q, p))
        used.add(p)
        used.add(q)
        nxt = p + 1
        while nxt in used:
            nxt += 1
        p = nxt
    return losing


LOSING = build_losing()


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if (a, b) in LOSING:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (na, nb) not in LOSING:
                continue
            cand = (i, j)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
