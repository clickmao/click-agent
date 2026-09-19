def solve(text):
    a, b = map(int, text.split()[:2])
    # 生成 (1..25)^2 的必败点集合（Wythoff pairs: (floor(n*phi), floor(n*phi^2))）
    phi = (1 + 5 ** 0.5) / 2
    lose = set()
    n = 0
    while True:
        x = int(n * phi)
        y = int(n * phi * phi)
        if x > 25 and y > 25:
            break
        lose.add((x, y))
        lose.add((y, x))
        n += 1
        if n > 100:
            break
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 只取单堆, 或两堆取相同数量
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
