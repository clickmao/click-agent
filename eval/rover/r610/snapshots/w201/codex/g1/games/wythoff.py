"""Wythoff's game."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    maxn = max(a, b) + 1
    # losing position (p, q) pairs: q = 1 (p+q) - p form; standard formula
    lose = set()
    n = 0
    while True:
        p = 1
        # brute: find losing positions up to maxn via mex method
        break

    used = set()
    n = 0
    while True:
        while n in used:
            n += 1
        p = n
        q = p + n
        if p > maxn and q > maxn:
            break
        used.add(p)
        used.add(q)
        lose.add((p, q))
        lose.add((q, p))
        n += 1

    if (a, b) in lose:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in lose:
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
