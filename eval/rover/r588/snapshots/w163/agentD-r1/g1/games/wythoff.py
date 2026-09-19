def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    na, nb = a, b
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 单堆取
            if i == 0 or j == 0:
                x, y = a - i, b - j
                if (x == 0 or y == 0) and x + y > 0 or True:
                    pass
            # 同时同数取不在此处枚举: 用直接判定
        break
    # 直接用必败点公式判定, 并枚举最小字典序必胜着法
    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        k = int(d * ((5 ** 0.5 + 1) / 2))
        for kk in (k - 1, k, k + 1):
            if kk >= 0 and (int(kk * ((5 ** 0.5 + 1) / 2)), int(kk * ((5 ** 0.5 + 1) / 2)) + kk) == (x, y):
                return True
        return False
    if losing(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing(a - i, b - j):
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
