def solve(text):
    lines = text.splitlines()
    if not lines:
        return 'LOSE'
    head = lines[0].split()
    if not head:
        return 'LOSE'
    a = int(head[0])
    b = int(head[1]) if len(head) > 1 else 0
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            na = a - i
            nb = b - j
            lo = min(na, nb)
            hi = max(na, nb)
            d = hi - lo
            if lo == int(d * 1.618033988749895) and lo == int((d * (1 + 5 ** 0.5)) / 2):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
