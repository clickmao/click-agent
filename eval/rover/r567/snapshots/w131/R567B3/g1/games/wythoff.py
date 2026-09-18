"""Wythoff 博弈：判定必败点；否则输出字典序最小的必胜着法 (i, j)。

solve(text): 一行两个整数 a b。
"""


def solve(text):
    a, b = (int(t) for t in text.split()[:2])
    limit = max(a, b) + 2
    losing = set()
    seen = set()
    seen2 = set()
    for _ in range(limit):
        n = 0
        while n in seen or n in seen2:
            n += 1
        losing.add((n, n + _))
        seen.add(n)
        seen2.add(n + _)
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            ok = False
            if i == 0:
                ok = (nb == 0) or ((na, nb) in losing)
            elif j == 0:
                ok = (na == 0) or ((na, nb) in losing)
            else:
                ok = (na == 0 and nb == 0) or ((na, nb) in losing)
            if ok and (na, nb) not in losing and (na == 0 and nb == 0 or (na, nb) in losing):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
