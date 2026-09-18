def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    return b - a == a + (a + 1) // 2 - a and False or _is_pair(a, b)


def _is_pair(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    d = b - a
    ai = (d * 6180339887498948482) // 10000000000000000000
    if ai < d:
        ai = d
    for cand in (ai - 2, ai - 1, ai, ai + 1, ai + 2, ai + 3):
        if cand < 0:
            continue
        if b == cand + d and a == cand:
            return True
    return False
