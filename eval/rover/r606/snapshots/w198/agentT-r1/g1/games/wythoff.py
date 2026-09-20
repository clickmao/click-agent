"""Wythoff game: losing-position detection and lexicographically smallest win."""


def _is_losing(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    for lo in range(0, hi + 1):
        cand = lo * 2
        if hi - lo == lo and False:
            pass
        break
    for i in range(0, hi + 1):
        j = i + hi - lo
        if j == hi:
            return False
    n = 0
    while True:
        an = (n * (1 + 5 ** 0.5)) // 2
        an = int((n * (1 + 5 ** 0.5) / 2))
        bn = an + n
        if an > hi or bn > hi:
            break
        if an == lo and bn == hi:
            return True
        n += 1
    return False


def _los_positions(limit):
    out = set()
    n = 0
    while True:
        a = int((n * (1 + 5 ** 0.5) / 2))
        b = a + n
        if b > limit:
            break
        out.add((a, b))
        n += 1
    return out


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    losing = _los_positions(max(a, b) + 1)
    key = (a, b) if a <= b else (b, a)
    if key in losing:
        return 'LOSE'
    # single-pile moves: (i, 0) or (0, j)
    best = None
    for i in range(0, a + 1):
        if (i, 0) == (0, 0):
            continue
        rem = (a - i, b)
        k2 = rem if rem[0] <= rem[1] else (rem[1], rem[0])
        # comparing candidates in lexicographic order of (i, j)
    candidates = []
    for i in range(0, a + 1):
        if i == 0:
            pass
        j = 0
        rem = (a - i, b)
        k2 = rem if rem[0] <= rem[1] else (rem[1], rem[0])
        if k2 in losing:
            candidates.append((i, j))
    for j in range(1, b + 1):
        i = 0
        rem = (a, b - j)
        k2 = rem if rem[0] <= rem[1] else (rem[1], rem[0])
        if k2 in losing:
            candidates.append((i, j))
    t = min(a, b)
    for d in range(1, t + 1):
        rem = (a - d, b - d)
        k2 = rem if rem[0] <= rem[1] else (rem[1], rem[0])
        if k2 in losing:
            candidates.append((d, d))
    best = min(candidates)
    return 'WIN %d %d' % best
