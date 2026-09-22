import math


def solve(text: str) -> str:
    data = text.split()
    if len(data) < 2:
        return ''
    a, b = int(data[0]), int(data[1])
    golden = (1 + math.sqrt(5)) / 2
    losing = set()
    t = 0
    while True:
        u = int(math.floor(t * golden))
        v = u + t
        if u > 25 or v > 25:
            break
        losing.add((u, v))
        losing.add((v, u))
        t += 1

    def is_lose(p, q):
        if p > q:
            p, q = q, p
        return (p, q) in losing and (p, q) != (0, 0)

    if is_lose(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            ni, nj = a - i, b - j
            if (ni == 0 and nj == 0) or is_lose(ni, nj):
                cands.append((i, j))
    cands.sort()
    if cands:
        i, j = cands[0]
        return 'WIN %d %d' % (i, j)
    return 'LOSE'
