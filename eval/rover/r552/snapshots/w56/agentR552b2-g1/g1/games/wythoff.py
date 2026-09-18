def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    a, b = (int(x) for x in lines[0].split()[:2])
    if a > b:
        lo, hi = b, a
    else:
        lo, hi = a, b
    phi = (1 + 5 ** 0.5) / 2
    is_lose = False
    t = int(hi / phi) - 2
    for cand in range(max(t, 0), max(t, 0) + 5):
        if cand >= 0 and cand + 1 + cand == hi and cand == lo:
            is_lose = True
            break
        if cand >= 0 and int(cand * phi) + cand == hi and int(cand * phi) == lo:
            is_lose = True
            break
    if is_lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            x, y = (na, nb) if na <= nb else (nb, na)
            bad = False
            tt = int(y / phi) - 2
            for cand in range(max(tt, 0), max(tt, 0) + 5):
                if cand >= 0 and int(cand * phi) == x and int(cand * phi) + cand == y:
                    bad = True
                    break
            if bad:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
