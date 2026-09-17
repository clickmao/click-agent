def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split())

    # grundy / losing positions for Wythoff game on (a, b)
    def is_losing(x, y):
        lo, hi = min(x, y), max(x, y)
        # losing iff (lo, hi) == (floor(t*phi), floor(t*phi^2)) for some t
        import math
        t = hi - lo
        if t < 0:
            return False
        # candidate: lo == floor(t*phi), hi == floor(t*phi^2) where phi=(1+sqrt5)/2
        phi = (1 + math.sqrt(5)) / 2
        # check by computing t from lo
        # floor(t*phi)=lo => t = floor((lo+1)/phi) roughly; verify directly
        cand = int(lo / phi)
        for tt in (cand - 1, cand, cand + 1):
            if tt >= 0:
                l2 = int(tt * phi)
                h2 = int(tt * phi * phi)
                if l2 == lo and h2 == hi:
                    return True
        return False

    if is_losing(a, b):
        return 'LOSE'

    best = None
    # move type (i): take from one pile only
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if (i == 0) or (j == 0):
                if is_losing(ni, nj):
                    if best is None or (i, j) < best:
                        best = (i, j)
            # move type (ii): equal from both
            if i == j and i > 0:
                if is_losing(ni, nj):
                    if best is None or (i, j) < best:
                        best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % (best[0], best[1])
