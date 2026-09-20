def solve(text: str) -> str:
    a, b = map(int, text.split())
    lo, hi = min(a, b), max(a, b)
    cold = set()
    n = 0
    while True:
        x = (n * 1618033989) // 1000000000
        y = x + n
        if x > 25 and y > 25:
            break
        if x <= 25 and y <= 25:
            cold.add((x, y))
        n += 1
        if n > 100:
            break
    if (lo, hi) in cold:
        return 'LOSE'
    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na = a - i
            nb = b - j
            l2, h2 = min(na, nb), max(na, nb)
            if (l2, h2) in cold:
                candidates.append((i, j))
    candidates.sort()
    return 'WIN ' + str(candidates[0][0]) + ' ' + str(candidates[0][1])
