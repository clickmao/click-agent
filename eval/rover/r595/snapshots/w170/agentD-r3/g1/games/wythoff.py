def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    parts = lines[idx].split()
    a = int(parts[0])
    b = int(parts[1])
    import math
    aa, bb = (a, b) if a <= b else (b, a)
    # losing positions: (floor(m*phi), floor(m*phi)+m)
    phi = (1 + math.sqrt(5)) / 2
    m = int(bb - aa)
    losing = False
    if aa == int(math.floor(m * phi)):
        losing = True
    if losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            u, v = (na, nb) if na <= nb else (nb, na)
            d = v - u
            if u == int(math.floor(d * phi)):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
