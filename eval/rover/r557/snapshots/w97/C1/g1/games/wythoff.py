def solve(text: str) -> str:
    a, b = map(int, text.split())
    LOSE = set()
    for i in range(0, 40):
        A = int(i * (1 + 5 ** 0.5) / 2)
        B = A + i
        if A > 25 and B > 25:
            break
        LOSE.add((A, B))
        LOSE.add((B, A))
    if (a, b) in LOSE:
        return 'LOSE'
    best = None
    for di in range(0, a + 1):
        for dj in range(0, b + 1):
            if di == 0 and dj == 0:
                continue
            na, nb = a - di, b - dj
            if (na == a and nb == b) or not (na == a or nb == b or di == dj):
                continue
            if (na, nb) in LOSE:
                best = (di, dj)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
