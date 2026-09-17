def solve(text: str) -> str:
    a, b = map(int, text.split())
    # 必败点: (floor(j*phi), floor(j*phi)+j)
    lose = set()
    x, y = 0, 0
    while y <= 25:
        lose.add((x, y))
        lose.add((y, x))
        x += 1
        y = x * 2
    # 更稳妥: 直接打表双堆 <=25 的必败点
    lose = set()
    for j in range(0, 60):
        p = (j * 1618033) // 1000000  # floor(j*phi) 近似
        q = p + j
        if p > 25 or q > 25:
            break
        lose.add((p, q))
        lose.add((q, p))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
