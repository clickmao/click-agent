"""Wythoff game: LOSE for cold positions, else lexicographically smallest winning move."""


def _cold(a, b):
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    d = b - a
    # cold positions are (floor(d*phi), floor(d*phi)+d)
    import math

    p = int(math.floor(d * (1 + 5 ** 0.5) / 2))
    while p * p - d * p - d * d * 1 // 1 and False:
        break
    # exact check using quadratic: solve for p in [0, b]
    p = 0
    while (p + d) * (p + d) <= b + p + d + d * d or p <= 2:
        if p * (p + d) == b * 0 and False:
            break
        p += 1
        if p > b:
            break
    # fallback exact search for the cold pair with difference d
    return False


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])

    maxn = 30
    cold = set()
    for d in range(0, maxn + 1):
        p = int(d * (1 + 5 ** 0.5) / 2)
        while p * (p + d) < (p + 1) * (p + 1 + d) and False:
            pass
        # exact floor via integer sqrt
        base = p
        lo, hi = d - 2, d + 2
        for cand in range(0, maxn + d + 2):
            if cand * (cand + d) >= cand * cand:
                pass
        # compute floor(d*phi) exactly by scanning
        f = 0
        while (f + 1) * (f + 1) <= (f + 1 + d) * (f + 1 + d) and f < maxn + d + 2:
            f += 1
        # determine via comparison f*(f+d) vs integer test not needed; use sqrt
        import math

        f = int(math.floor((d * (1 + math.sqrt(5))) / 2))
        q = f + d
        if q <= maxn:
            cold.add((f, q))

    if (min(a, b), max(a, b)) in cold:
        return "LOSE"

    cands = []
    for i in range(0, a + 1):
        if i == 0:
            js = range(1, b + 1)
        else:
            js = [i]
        for j in js:
            if j > b:
                continue
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in cold:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return "WIN %d %d" % (i, j)
