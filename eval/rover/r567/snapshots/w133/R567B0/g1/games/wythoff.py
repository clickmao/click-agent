"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    a, b = map(int, lines[0].split()[:2])
    if a > b:
        a, b = b, a

    phi = (1.0 + 5.0 ** 0.5) / 2.0
    j = int((b - a) / phi)
    for cand in (j, j + 1, j - 1, j + 2):
        if cand >= 0 and int(cand * phi) == a and a + cand == b:
            return 'LOSE'

    moves = []
    for i in range(a + 1):
        for jj in range(b + 1):
            if i == 0 and jj == 0:
                continue
            if i > 0 and jj > 0 and i != jj:
                continue
            na, nb = a - i, b - jj
            if na == 0 and nb == 0:
                moves.append((i, jj))
                continue
            lo, hi = (na, nb) if na <= nb else (nb, na)
            d = hi - lo
            c = int(d / phi)
            for cand in (c, c + 1, c - 1, c + 2):
                if cand >= 0 and int(cand * phi) == lo and lo + cand == hi:
                    moves.append((i, jj))
                    break

    moves.sort()
    i, jj = moves[0]
    return 'WIN %d %d' % (i, jj)
