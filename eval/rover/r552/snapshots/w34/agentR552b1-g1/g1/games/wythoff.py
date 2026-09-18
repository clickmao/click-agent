def _wythoff_lose(a, b):
    x, y = sorted((a, b))
    # max coordinate for wythoff lose pairs (Bean's formula)
    limit = x + y + 5
    lose = set()
    for n in range(limit + 1):
        an = n * (1 + 5 ** 0.5) / 2.0
        bn = an + n
        an = int(an + 0.5)
        bn = an + n
        if an > 25 + 25:
            break
        lose.add((an, bn))
    return (x, y) in lose


def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if (i == 0 or j == 0 or i == j):
                if _wythoff_lose(na, nb):
                    candidates.append((i, j))
    if not candidates:
        return 'LOSE'
    candidates.sort()
    i, j = candidates[0]
    return 'WIN %d %d' % (i, j)
