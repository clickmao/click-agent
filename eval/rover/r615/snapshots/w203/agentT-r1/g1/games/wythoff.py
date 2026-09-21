def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    n = 0
    while n <= 30:
        p = int(n * phi)
        q = int(n * phi * phi)
        losing.add((p, q))
        losing.add((q, p))
        n += 1
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = (a - i, b) in losing
            elif i == 0 and j > 0:
                ok = (a, b - j) in losing
            elif i == j and i > 0:
                ok = (a - i, b - j) in losing
            if ok:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
