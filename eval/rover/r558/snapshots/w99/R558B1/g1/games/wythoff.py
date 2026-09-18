def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    n = max(a, b)
    losing = set()
    used = set()
    for k in range(0, n + 1):
        x, y = k, k + k
        while x in used or y in used or x == y:
            x += 1
            y += 1
        used.add(x)
        used.add(y)
        losing.add((x, y))
        if x > n and y > n and k > 0 and y > n:
            if x > n:
                break
    def is_lose(p, q):
        lo, hi = min(p, q), max(p, q)
        return (lo, hi) in losing
    if is_lose(a, b):
        return 'LOSE'
    best = None
    i = 0
    while i <= a:
        j = 0
        while j <= b:
            if i == 0 and j == 0:
                j += 1
                continue
            na, nb = a - i, b - j
            if is_lose(na, nb):
                best = (i, j)
                break
            j += 1
        if best is not None:
            break
        i += 1
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
