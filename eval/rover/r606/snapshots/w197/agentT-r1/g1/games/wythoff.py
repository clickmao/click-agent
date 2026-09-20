"""Wythoff's game: detect losing positions, else lexicographically smallest move."""

LIM = 26


def _make_losing():
    losing = set()
    for x in range(LIM + 1):
        for y in range(LIM + 1):
            if x == 0 and y == 0:
                losing.add((0, 0))
                continue
            ok = True
            for i in range(0, x + 1):
                for j in range(0, y + 1):
                    if i == 0 and j == 0:
                        continue
                    if i != 0 and j != 0 and i != j:
                        continue
                    if (x - i, y - j) in losing:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                losing.add((x, y))
    return losing


_LOSING = _make_losing()


def solve(text):
    line = text.splitlines()[0]
    a, b = (int(x) for x in line.split())
    if (a, b) in _LOSING:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in _LOSING:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
