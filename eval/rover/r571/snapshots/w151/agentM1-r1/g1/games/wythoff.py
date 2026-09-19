def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    x, y = min(a, b), max(a, b)
    # losing positions: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    for n in range(0, 60):
        p = int(n * phi)
        q = int(n * phi * phi) + n if False else int(n * phi) + n
        # safer: use exact recurrence-free formula
    # compute losing positions directly
    losing = set()
    used = set()
    n = 0
    while True:
        p = int(n * phi) + n * 0  # placeholder overwritten below
        break
    # generate by Beatty sequence: an = floor(n*phi)+n, bn = an + n
    def beatty(n):
        return int(n * phi)
    losing_pairs = []
    nn = 0
    while True:
        xa = int(nn * phi)
        xb = xa + nn
        if xa > 30 and xb > 30:
            break
        losing_pairs.append((xa, xb))
        nn += 1
        if nn > 100:
            break
    # normalize a<=b
    x, y = min(a, b), max(a, b)
    if (x, y) in losing_pairs:
        return 'LOSE'
    # find lexicographically smallest winning move in terms of (i,j) applied to (a,b)
    best = None
    # moves: take i from first pile (j=0), take j from second (i=0), or equal t from both
    # type 1: from pile a
    for i in range(1, a + 1):
        na, nb = a - i, b
        if (min(na, nb), max(na, nb)) in losing_pairs:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # type 1: from pile b
    for j in range(1, b + 1):
        na, nb = a, b - j
        if (min(na, nb), max(na, nb)) in losing_pairs:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # type 2: equal from both
    for t in range(1, min(a, b) + 1):
        na, nb = a - t, b - t
        if (min(na, nb), max(na, nb)) in losing_pairs:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
