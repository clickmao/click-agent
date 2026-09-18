def _losing(a, b, limit):
    seen = set()
    lst = []
    n = 0
    while True:
        q = int(n * ((1 + 5 ** 0.5) / 2))
        p = q + n
        if p > limit and q > limit:
            break
        if (p, q) not in seen and (q, p) not in seen:
            seen.add((p, q))
            lst.append((p, q))
        n += 1
    return set(lst)


def solve(text: str) -> str:
    ints = text.split()
    a = int(ints[0])
    b = int(ints[1])
    limit = max(a, b) + 2
    losing = _losing(a, b, limit)
    check = set()
    for (p, q) in losing:
        check.add((p, q))
        check.add((q, p))
    if (a, b) in check:
        return "LOSE"
    best = None
    for i in range(a + 1):
        j = b - (a - i)
        if 0 <= j <= b and (i, j) != (0, 0):
            if (a - i, b - j) in check:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        for j in range(b + 1):
            if j != 0 and (a, b - j) in check:
                cand = (0, j)
                if best is None or cand < best:
                    best = cand
            if j <= a and j != 0 and (a - j, b) in check:
                cand = (j, 0)
                if best is None or cand < best:
                    best = cand
    if best is None:
        for i in range(a + 1):
            j = b - (a - i)
            if 0 <= j <= b and (i, j) != (0, 0) and (a - i, b - j) in check:
                best = (i, j)
                break
    return "WIN %d %d" % best
