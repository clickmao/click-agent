"""Wythoff 博弈。"""


def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    losing = set()
    used = set()
    k = 0
    while True:
        n = 0
        while n in used:
            n += 1
        xn = n
        yn = xn + k
        if xn > 25 and yn > 25:
            break
        used.add(xn)
        used.add(yn)
        losing.add((min(xn, yn), max(xn, yn)))
        k += 1

    if (min(a, b), max(a, b)) in losing:
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            ra, rb = a - i, b - j
            if (min(ra, rb), max(ra, rb)) in losing:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
