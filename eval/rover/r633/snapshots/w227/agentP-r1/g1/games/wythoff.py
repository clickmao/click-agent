def _is_lose(a, b):
    d = abs(a - b)
    lo = min(a, b)
    return lo == int(d * (5 ** 0.5 + 1) / 2)


def solve(text):
    a, b = map(int, text.split())
    if _is_lose(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (j > 0 and i == 0) or (i == j):
                if _is_lose(a - i, b - j):
                    cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
