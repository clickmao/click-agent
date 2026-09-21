def _lose_table(limit):
    lose = set()
    used = set()
    i = 0
    while True:
        while i in used:
            i += 1
        j = i + 1
        while j in used:
            j += 1
        if j > limit:
            break
        lose.add((i, j))
        lose.add((j, i))
        used.add(i)
        used.add(j)
        i += 1
    return lose


def solve(text):
    a, b = map(int, text.split())
    limit = max(a, b)
    lose = _lose_table(limit)
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
