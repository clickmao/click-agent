def _losing_positions(limit):
    losing = set()
    used = set()
    n = 0
    while True:
        a = n
        while a in used:
            a += 1
        b = a + n
        if a > limit and b > limit:
            break
        losing.add((a, b))
        losing.add((b, a))
        used.add(a)
        used.add(b)
        n += 1
    return losing


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    losing = _losing_positions(25)
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
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
