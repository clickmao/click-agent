def _losing_set(limit):
    pairs = set()
    for x in range(limit + 1):
        for y in range(x, limit + 1):
            if (x, y) in pairs:
                continue
            ok = True
            for (px, py) in pairs:
                if x == px or y == py or (y - x) == (py - px):
                    ok = False
                    break
            if ok:
                pairs.add((x, y))
    return pairs


_LOSE = _losing_set(25 + 12)


def _is_losing(x, y):
    if x > y:
        x, y = y, x
    return (x, y) in _LOSE


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
