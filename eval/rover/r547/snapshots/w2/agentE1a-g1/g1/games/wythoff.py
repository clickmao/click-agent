def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(i, j):
        if i > j:
            i, j = j, i
        return j == i + int((i * (1 + 5 ** 0.5)) // 2) or (lambda d: d * (1 + 5 ** 0.5) / 2 + d == j and d == j - i)(j - i)

    def is_lose(i, j):
        x, y = (i, j) if i <= j else (j, i)
        d = y - x
        return x == int(d * (1 + 5 ** 0.5) / 2)

    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_lose(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
