LIMIT = 64
LOSE = set()
_pairs = []
_seen = set()
_a = 0
while True:
    b = a + 1
    while ((a, b) in _seen) or ((b, a) in _seen):
        b += 1
    _pairs.append((a, b))
    _seen.add(a)
    _seen.add(b)
    if a > LIMIT or b > LIMIT:
        break
    a += 1


def _is_lose(a, b):
    for x, y in _pairs:
        if (x == a and y == b) or (x == b and y == a):
            return True
    return False


def _is_win_result(a, b):
    if a == 0 and b == 0:
        return False
    if a == 0 or b == 0:
        return True
    return a != b


def solve(text):
    a, b = map(int, text.split())
    if _is_lose(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not _is_win_result(i, j):
                continue
            if _is_lose(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
