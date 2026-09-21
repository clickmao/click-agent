"""Wythoff 博弈: 判定必败点, 否则给出字典序最小的必胜着法 (i, j)。

solve(text) 读入一行两个整数 a b。
规则: 每次从任意一堆取任意正数, 或从两堆同时取相同正数, 取走最后一颗者胜。
返回: 'LOSE' 或 'WIN i j' (i, j >= 0 且不同时为 0, 按字典序最小)。
"""


def _lost(a, b):
    # 必败点: (floor(k*phi), floor(k*phi^2)), 无序对
    if a > b:
        a, b = b, a
    # phi^2 = phi + 1, 直接用整数形式判定
    # Wythoff 必败对: b - a = k, a = floor(k * (1+sqrt5)/2)
    d = b - a
    k = int(d * 1.618033988749895) - 2
    for kk in (k - 1, k, k + 1, k + 2):
        if kk < 0:
            continue
        # floor(kk * phi) 用整数精确值验证
        m = (1 + 5 ** 0.5) / 2
        if int(kk * m) == a and int(kk * m * m) == b:
            return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _lost(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 只减第一堆 / 只减第二堆 / 两堆同减
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                if _lost(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
    i, j = best
    return 'WIN %d %d' % (i, j)
