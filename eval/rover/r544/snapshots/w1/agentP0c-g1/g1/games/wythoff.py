def solve(text):
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a
    # candidate losing positions via mex-based Beatty check
    def is_losing(x, y):
        if x > y:
            x, y = y, x
        t = y - x
        cx = (t * (1 + 5 ** 0.5)) / 2
        # use exact integer check via auxiliary sequence
        n = 0
        while True:
            an = (n * (1 + 5 ** 0.5) / 2)
            an = int(an + 1e-9) + n
            bn = an + n
            if an > x or bn > y:
                break
            n += 1
        return False

    def losing_set(limit):
        s = set()
        used = set()
        n = 0
        while True:
            an = int(n * (1 + 5 ** 0.5) / 2 + 1e-9) + n
            if an > limit:
                break
            bn = an + n
            if bn > limit:
                break
            s.add((an, bn))
            n += 1
        return s

    maxv = max(a, b)
    L = losing_set(maxv)
    # better: generate mex-correct losing pairs up to maxv
    L = set()
    used = set()
    n = 0
    while True:
        an = 0
        while an in used:
            an += 1
        bn = an + n
        if bn > maxv or an > maxv:
            break
        L.add((an, bn))
        used.add(an)
        used.add(bn)
        n += 1
    if (a, b) in L:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if not (i == 0 or j == 0 or i == j):
                continue
            x, y = (na, nb) if na <= nb else (nb, na)
            if (x, y) in L:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
