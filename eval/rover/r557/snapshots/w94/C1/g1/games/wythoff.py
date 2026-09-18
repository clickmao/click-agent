def solve(text: str) -> str:
    a, b = map(int, text.split())

    limit = max(a, b) * 2 + 10
    losing = set()
    used = set()
    n = 0
    while len(losing) // 2 <= limit:
        cand = 0
        while cand in used:
            cand += 1
        pair = (cand, cand + n)
        losing.add(pair)
        losing.add((pair[1], pair[0]))
        used.add(pair[0])
        used.add(pair[1])
        n += 1
        if n > limit:
            break

    if (a, b) in losing:
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                return 'WIN %d %d' % (i, j)
