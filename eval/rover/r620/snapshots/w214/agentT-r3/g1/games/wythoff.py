def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    # 必败点: (floor(n*phi), floor(n*phi*phi))
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        losing.add((y, x))
        n += 1
    if (a, b) in losing:
        return 'LOSE'
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # 合法: 只动一堆, 或两堆取相同数目
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in losing:
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN %d %d' % (i, j)
