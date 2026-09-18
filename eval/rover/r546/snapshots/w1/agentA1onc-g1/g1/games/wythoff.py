"""Wythoff 博弈必败点判定与字典序最小必胜着法。

solve(text) 读入: 一行两个整数 a b (两堆石子数)。
规则: 每次 (i) 从任意一堆取走任意正数, 或 (ii) 从两堆同时取走相同正数;
      取走最后一颗者胜。
输出: 先手必败 -> 'LOSE'; 否则 -> 'WIN i j'
      ((i, j) 为全部必胜着法中按字典序最小者, i,j>=0 且不同时为 0)。
"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    # 必然败点 (冷点): (floor(k*phi), floor(k*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    for k in range(1, 30):
        x = int(k * phi)
        y = int(k * phi * phi)
        if x > 25 and y > 25:
            break
        cold.add((x, y))
        cold.add((y, x))

    if (a, b) in cold:
        return 'LOSE'

    # 枚举所有着法, 找字典序最小 (先 i 后 j) 的必胜着法
    best = None
    # (i) 只动第一堆
    for i in range(0, a + 1):
        na, nb = a - i, b
        if na == a:
            continue
        if (na, nb) in cold:
            best = (i, 0)
            break
    # (i) 只动第二堆
    if best is None:
        for j in range(1, b + 1):
            if (a, b - j) in cold:
                best = (0, j)
                break
    if best is None:
        # (ii) 两堆同取
        d = min(a, b)
        for t in range(1, d + 1):
            if (a - t, b - t) in cold:
                best = (t, t)
                break
    i, j = best
    return 'WIN %d %d' % (i, j)
