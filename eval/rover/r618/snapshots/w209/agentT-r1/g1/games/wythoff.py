def solve(text: str) -> str:
    ab = text.split()
    a, b = int(ab[0]), int(ab[1])
    limit = max(a, b) + 1
    losing = set()
    for n in range(limit + 1):
        an = int(n * (1 + 5 ** 0.5) / 2)
        bn = an + n
        if an > limit or bn > limit:
            break
        losing.add((an, bn))
        losing.add((bn, an))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
