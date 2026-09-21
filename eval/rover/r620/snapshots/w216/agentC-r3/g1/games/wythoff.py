def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    losing = set()
    for n in range(0, 26):
        an = (n * (1 + 5 ** 0.5)) // 2
        while an in [p[0] for p in losing] or an in [q[1] for q in losing]:
            an += 1
        an = int(an)
        bn = an + n
        losing.add((an, bn))
        losing.add((bn, an))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
