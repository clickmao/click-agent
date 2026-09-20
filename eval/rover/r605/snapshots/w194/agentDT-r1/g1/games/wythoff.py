def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    limit = 30
    losing = set()
    seen = set()
    m = 0
    while True:
        while m in seen:
            m += 1
        x, y = m, m + len(losing) // 2 + 1
        if x > limit and y > limit:
            break
        losing.add((x, y))
        losing.add((y, x))
        seen.add(x)
        seen.add(y)
        m += 1

    if (a, b) in losing:
        return "LOSE"

    cands = []
    for i in range(1, a + 1):
        if (a - i, b) in losing:
            cands.append((i, 0))
    for j in range(1, b + 1):
        if (a, b - j) in losing:
            cands.append((0, j))
    for t in range(1, min(a, b) + 1):
        if (a - t, b - t) in losing:
            cands.append((t, t))
    cands.sort()
    i, j = cands[0]
    return "WIN " + str(i) + " " + str(j)
