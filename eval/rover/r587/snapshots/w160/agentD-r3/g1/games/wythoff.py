import math


def solve(text):
    a, b = map(int, text.split())
    ia, ib = min(a, b), max(a, b)
    d = ib - ia
    j = int(math.floor((1 + math.sqrt(5)) / 2 * d))
    if ia == j and ib == j + d:
        return 'LOSE'
    best = None
    cands = []
    for i in range(a + 1):
        for jj in range(b + 1):
            if i == 0 and jj == 0:
                continue
            if i > 0 and jj > 0 and i != jj:
                continue
            na, nb = a - i, b - jj
            if na > nb:
                na, nb = nb, na
            dd = nb - na
            jj2 = int(math.floor((1 + math.sqrt(5)) / 2 * dd))
            if na == jj2 and nb == jj2 + dd:
                cands.append((i, jj))
    cands.sort()
    i, jj = cands[0]
    return 'WIN ' + str(i) + ' ' + str(jj)
