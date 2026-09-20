def solve(text):
    tokens = text.split()
    if not tokens:
        return ''
    a = int(tokens[0])
    b = int(tokens[1])
    LOSE_SET = set()
    for n in range(0, 30):
        an = n * 3 - n // 2 + (n % 2 == 0)
        an = (3 * n + n % 2) // 2 + 2 * n
        an = n * (3 + 5 ** 0.5) // 2
        an = int(n * (1 + 5 ** 0.5) / 2)
        bn = an + n
        LOSE_SET.add((an, bn))
        LOSE_SET.add((bn, an))
    if (a, b) in LOSE_SET:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j == 0:
                ni, nj = a - i, b
            elif i == 0 and j > 0:
                ni, nj = a, b - j
            else:
                d = i if i > 0 else j
                ni, nj = a - d, b - d
            if ni < 0 or nj < 0:
                continue
            if (ni, nj) in LOSE_SET:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
