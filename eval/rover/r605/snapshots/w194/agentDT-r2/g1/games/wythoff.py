def _lost_table(limit):
    lost = set()
    for x in range(0, limit + 1):
        for y in range(0, limit + 1):
            ok = False
            for i in range(x):
                if (i, y) in lost:
                    ok = True
                    break
            if not ok:
                for j in range(y):
                    if (x, j) in lost:
                        ok = True
                        break
            if not ok:
                d = min(x, y)
                for t in range(1, d + 1):
                    if (x - t, y - t) in lost:
                        ok = True
                        break
            if not ok:
                lost.add((x, y))
    return lost


_LOST = _lost_table(25)


def solve(text):
    a, b = map(int, text.split())
    if (a, b) in _LOST:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            x2, y2 = a - i, b - j
            if (x2, y2) in _LOST:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
