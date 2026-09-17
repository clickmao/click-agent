"""Wythoff 博弈：必败点判定 / 字典序最小的必胜着法。

读入: 一行 a b。
输出: 必败 "LOSE"; 否则 "WIN i j" (i>=0, j>=0, 不同时为 0, (i,j) 字典序最小)。
"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    def is_losing(x, y):
        # Wythoff 必败点: (floor(k*phi), floor(k*phi^2)), phi=(1+sqrt(5))/2,
        # 即冷点 差 d=y-x 满足 x == floor(d*phi)
        x, y = min(x, y), max(x, y)
        d = y - x
        # floor(d * (1+sqrt(5))/2) 用整数精确判定: floor(d*phi) == x ?
        # d*phi = d/2 + d*sqrt(5)/2 ; 用整数 sqrt 判定
        # 精确: x == floor(d*phi) 等价于 x^2 + d*x - d^2*? 用标准判定:
        return (x == (d * 5 ** 0.5 + d) // 2) if False else _cold(x, d)

    def _cold(x, d):
        # 精确判定 floor(d*(1+sqrt5)/2) == x  <=>  x <= d*phi < x+1
        #     等价于 d*phi >= x 且 d*phi < x+1
        # 用整数比较避免浮点误差: phi 的共轭 phi' = (1-sqrt5)/2
        # 判据: 令 t = floor(d*phi)，t 满足 t = x 当且仅当
        #       (2x - d)^2 < 5 d^2  且  x - d < 0 关系...
        # 直接使用稳定整数公式: t = (d*5**0.5 + d)//2 用 Decimal 不必要；
        # 用整数等价: floor(d*phi) = d + floor(d/phi')? 改用精确算法:
        return _floor_phi(d) == x

    def _floor_phi(d):
        # floor(d * (1+sqrt(5))/2) 精确整数计算: 二分
        lo, hi = 0, 2 * d + 2
        while lo < hi:
            mid = (lo + hi + 1) // 2
            # 判 mid <= d*phi  <=>  mid <= (d + d*sqrt5)/2
            #   <=>  2*mid - d <= d*sqrt5
            # 两边可能为负, 分情况比较
            lhs = 2 * mid - d
            if lhs <= 0:
                ok = True  # lhs<=0 <= d*sqrt5 (d>=0)
            else:
                ok = (lhs * lhs) <= 5 * d * d
            if ok:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def losing_pair(x, y):
        x, y = min(x, y), max(x, y)
        d = y - x
        return _floor_phi(d) == x

    if losing_pair(a, b):
        return 'LOSE'

    # 枚举所有着法, 取字典序最小的必胜着法
    best = None
    # (i) 从第一堆取 i: 新状态 (a-i, b)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 只取一堆 或 两堆同取
            if i == 0 or j == 0 or i == j:
                if losing_pair(a - i, b - j):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
                    # 已遍历到最小 i 的最小 j, 直接返回
                    return 'WIN %d %d' % (i, j)
    # 理论上不会有必败态之外无着法的情况, 兜底
    return 'LOSE'
