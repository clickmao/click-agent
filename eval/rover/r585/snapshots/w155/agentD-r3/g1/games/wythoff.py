def solve(text):
    a, b = [int(x) for x in text.split()[:2]]
    mex = a + b
    lost = set()
    for y in range(0, mex + 1):
        for x in range(0, y + 1):
            if (x, y) in lost or (y, x) in lost:
                continue
            covered = False
            for (px, py) in list(lost):
                if px == x or py == y or (y - py) == (x - px):
                    covered = True
                    break
            if not covered:
                lost.add((x, y))
            else:
                lost.add((x, y))
    state = (min(a, b), max(a, b))
    if state in lost:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            st = (min(na, nb), max(na, nb))
            if st in lost:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
