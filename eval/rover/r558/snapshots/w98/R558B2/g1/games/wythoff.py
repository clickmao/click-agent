def win(a, b):
    return _win(a, b)


_memo = {}


def _win(a, b):
    if a > b:
        a, b = b, a
    key = (a, b)
    if key in _memo:
        return _memo[key]
    res = False
    for i in range(1, a + 1):
        if not _win(a - i, b - i):
            res = True
            break
    if not res:
        for i in range(1, a + 1):
            if not _win(a - i, b):
                res = True
                break
    if not res:
        for j in range(1, b + 1):
            if not _win(a, b - j):
                res = True
                break
    _memo[key] = res
    return res


def solve(text):
    _memo.clear()
    _memo[(0, 0)] = False
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if not _win(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if not _win(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
