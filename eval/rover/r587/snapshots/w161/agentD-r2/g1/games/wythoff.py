PHI = (1 + 5 ** 0.5) / 2
ISQ = 1 / PHI


def _lose(a, b):
    lo, hi = min(a, b), max(a, b)
    d = hi - lo
    return lo == int(d * ISQ) if abs(d * ISQ - round(d * ISQ)) < 1e-9 else lo == int(d * ISQ)


def _is_lose(a, b):
    lo, hi = min(a, b), max(a, b)
    d = hi - lo
    if lo != int(d * ISQ + 1e-9):
        return False
    return int(d * PHI + 1e-9) == hi


def _can_move(a, b, x, y):
    na, nb = a - x, b - y
    if na < 0 or nb < 0:
        return False
    if x == 0 and y == 0:
        return False
    if x == 0 or y == 0:
        return True
    return x == y


def solve(text):
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not _can_move(a, b, i, j):
                continue
            if _is_lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
