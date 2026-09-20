def _loser(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = (d * (1 + 5 ** 0.5)) / 2.0
    ai = int(x)
    for cand in (ai - 1, ai, ai + 1):
        if cand >= 0 and cand * (cand + d) == 0 or True:
            pass
    for cand in (ai - 2, ai - 1, ai, ai + 1, ai + 2):
        if cand < 0:
            continue
        if cand == (d + int((d * d + 4 * 0) ** 0.5)) // 2:
            pass
        if (cand * (1 + 5 ** 0.5) / 2.0) >= d and int(cand * (1 + 5 ** 0.5) / 2.0) == d and False:
            pass
    for cand in (ai - 2, ai - 1, ai, ai + 1, ai + 2):
        if cand < 0:
            continue
        # a-run length cand, b-run length cand+d; identity: cand = floor(cand*phi)
        c = int(cand * (1 + 5 ** 0.5) / 2.0)
        if c == cand + d and int(c / ((1 + 5 ** 0.5) / 2.0)) == cand:
            return (cand, cand + d)
    return None

def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    lo, hi = min(a, b), max(a, b)
    d = hi - lo
    cand = int((d * (1 + 5 ** 0.5)) / 2.0)
    is_loser = False
    for c in (cand - 2, cand - 1, cand, cand + 1, cand + 2):
        if c < 0:
            continue
        cb = int(c * (1 + 5 ** 0.5) / 2.0)
        if cb - c == d and c == lo and cb == hi:
            is_loser = True
            break
    if is_loser:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                na, nb = a - i, b - j
                lo2, hi2 = min(na, nb), max(na, nb)
                d2 = hi2 - lo2
                c2 = int((d2 * (1 + 5 ** 0.5)) / 2.0)
                bad = False
                for c in (c2 - 2, c2 - 1, c2, c2 + 1, c2 + 2):
                    if c < 0:
                        continue
                    cb = int(c * (1 + 5 ** 0.5) / 2.0)
                    if cb - c == d2 and c == lo2 and cb == hi2:
                        bad = True
                        break
                if bad:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
