MAXN = 64


def _build_losing():
    losing = set()
    used_x = set()
    used_y = set()
    pairs = []
    a = 0
    while len(pairs) < MAXN:
        if a in used_x:
            a += 1
            continue
        b = a + 1
        while b in used_y:
            b += 1
        pairs.append((a, b))
        used_x.add(a)
        used_y.add(b)
        a += 1
    return pairs


_LOSING = _build_losing()
_LOSING_SET = set(_LOSING)


def _norm(a, b):
    return (a, b) if a <= b else (b, a)


def _is_losing(x, y):
    if x < 0 or y < 0:
        return False
    return _norm(x, y) in _LOSING_SET


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j == 0:
                pass
            elif i == 0 and j > 0:
                pass
            elif i == j:
                pass
            else:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
