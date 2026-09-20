def _pairs(limit):
    pts = set()
    used = set()
    m = 0
    while True:
        a = m
        while a in used:
            a += 1
        b = a + m
        if b > limit:
            break
        used.add(a)
        used.add(b)
        pts.add((a, b))
        pts.add((b, a))
        m += 1
    return pts


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split()[:2])

    pts = _pairs(max(a, b))
    if (a, b) in pts:
        return "LOSE"

    cands = []
    cands.append((a, b))
    cands.append((a, 0))
    cands.append((0, b))
    T = min(a, b)
    for k in range(1, T + 1):
        cands.append((k, k))

    best = None
    for i, j in cands:
        if i == 0 and j == 0:
            continue
        if i > a or j > b:
            continue
        if i > 0 and j > 0 and i != j:
            continue
        if (a - i, b - j) in pts:
            if best is None or (i, j) < best:
                best = (i, j)

    i, j = best
    return "WIN " + str(i) + " " + str(j)
