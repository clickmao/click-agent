"""Wythoff game: losing positions and the lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[0:2])

    n = max(a, b) * 2 + 10
    losing = set()
    for x in range(n + 1):
        for y in range(x, n + 1):
            ok = True
            for i in range(1, x + 1):
                if (x - i, y) in losing:
                    ok = False
                    break
            if ok:
                for j in range(1, y + 1):
                    nx, ny = (x, y - j) if x <= y - j else (y - j, x)
                    if (nx, ny) in losing:
                        ok = False
                        break
            if ok:
                for t in range(1, min(x, y) + 1):
                    p, q = x - t, y - t
                    nx, ny = (p, q) if p <= q else (q, p)
                    if (nx, ny) in losing:
                        ok = False
                        break
            if ok:
                losing.add((x, y))

    if (min(a, b), max(a, b)) in losing:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            x, y = a - i, b - j
            if (min(x, y), max(x, y)) in losing:
                best = (i, j)
                return 'WIN %d %d' % best
    return 'LOSE'
