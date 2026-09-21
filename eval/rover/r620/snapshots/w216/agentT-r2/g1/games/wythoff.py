def solve(text):
    lines = text.split('\n')
    parts = lines[0].split()
    a, b = int(parts[0]), int(parts[1])
    losing = set()
    for n in range(0, 40):
        an = int((n * (1 + 5 ** 0.5)) // 2)
        bn = an + n
        losing.add((an, bn))
        losing.add((bn, an))
    if (a, b) in losing:
        return 'LOSE'
    cands = []
    for i in range(1, a + 1):
        cands.append((i, 0))
    for j in range(1, b + 1):
        cands.append((0, j))
    d = min(a, b)
    for t in range(1, d + 1):
        cands.append((t, t))
    cands.sort()
    for i, j in cands:
        if (a - i, b - j) in losing:
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
