def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    losing = set()
    for n in range(0, 30):
        p = (n * (1 + 5 ** 0.5)) // 2
        q = p + n
        losing.add((p, q))
        losing.add((q, p))
    if (a, b) in losing:
        return "LOSE"
    n = a + b
    # (i, j) with i from first pile, j from second pile, lexicographically minimal
    best_i = None
    for j in range(0, 26):
        for i in range(0, 26):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if ni < 0 or nj < 0:
                continue
            if ni == 0 and nj == 0:
                continue
            if (ni, nj) in losing:
                best_i, best_j = i, j
                return "WIN %d %d" % (i, j)
    return "LOSE"
