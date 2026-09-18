def _pairs(limit):
    bad = set()
    n = 0
    while True:
        a = n
        while (a, a + n) in bad or (a + n, a) in bad:
            a += 1
        b = a + n
        if a > limit and b > limit:
            break
        bad.add((a, b))
        bad.add((b, a))
        n += 1
    return bad


BAD = _pairs(60)


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    a, b = map(int, lines[0].split())
    if (a, b) in BAD:
        return 'LOSE'
    cands = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            same = i == j
            one = (i == 0) or (j == 0)
            if not (same or one):
                continue
            if (a - i, b - j) in BAD:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
