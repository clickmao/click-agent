def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = (1 + 5 ** 0.5) / 2
    ai = int(d * x)
    for c in (ai - 2, ai - 1, ai, ai + 1, ai + 2):
        if c >= 0 and c + d == int(c * x + 0.5) and c == a and c + d == b:
            return True
    return False


def solve(text):
    a, b = map(int, text.strip().split()[:2])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        cand = [(i, 0)] if i > 0 else []
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            cand.append((i, j))
        for (x, y) in cand:
            if _is_losing(a - x, b - y):
                if best is None or (x, y) < best:
                    best = (x, y)
                break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
