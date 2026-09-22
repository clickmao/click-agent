"""Wythoff 博弈必败点判定。

输入格式：一行两个整数 ``a b``（1<=a<=25，1<=b<=25）两堆石子数。
玩法：每次可选 (i) 从任意一堆取走任意正数目的石子，或 (ii) 从两堆同时取走相同
正数目的石子；取走最后一颗者胜。
输出：先手必败输出 ``LOSE``；否则输出 ``WIN i j`` —— 从第一堆取 i 颗、第二堆取 j
颗，(i,j) 在全部必胜着法中按字典序最小（先比 i 再比 j；i,j>=0 且不同时为 0）。
"""


def _cold_at(lo, hi):
    """返回字典 {(x, y): True} 形式的 Wythoff 必败点，坐标为 (lo, hi) 与 (hi, lo)。"""
    return {(lo, hi), (hi, lo)}


def _cold_table(limit):
    """枚举所有坐标不超过 limit 的必败点集合（P-positions）。

    Wythoff 必败点第 k 对（k>=0）为 (floor(k*phi), floor(k*phi^2))，
    等价地 lo = k*(k+1)//2 不成立（那是错式），此处用 Beatty 精确整数判定：
    若 (x, y) 为必败点，则 min(x, y) 为第 k 个非 Beatty 数，可用
    k = y - x（差）唯一确定；判定 floor(k*phi) == x 且 x + k == y。
    """
    table = set()
    # 用整数迭代生成 Beatty 对，避免浮点误差：phi 的连分数近似
    # floor(k*phi) = floor(k * (1+sqrt(5))/2) 用整数 Newton 迭代求 sqrt(5) 的整数部分。
    k = 0
    while True:
        lo = _beatty(k)
        hi = lo + k
        if lo > limit:
            break
        if hi <= limit:
            table.add((lo, hi))
            table.add((hi, lo))
        k += 1
    return table


def _beatty(k):
    """返回 floor(k * phi)，phi = (1 + sqrt(5)) / 2，用整数运算保证精确。"""
    # floor(k*phi) = floor((k + k*sqrt(5)) / 2)；k*sqrt(5) 的整数部分用 isqrt。
    return (k + _isqrt_int(k * k * 5)) // 2


def _isqrt_int(x):
    """整数平方根（向下取整）。"""
    if x < 0:
        raise ValueError('negative')
    if x == 0:
        return 0
    r = int(x ** 0.5)
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) <= x:
        r += 1
    return r


def _cold_pairs(limit):
    """枚举所有坐标不超过 limit 的必败点 (lo, hi)，lo <= hi。"""
    pairs = []
    k = 0
    while True:
        lo = _beatty(k)
        hi = lo + k
        if lo > limit:
            break
        if hi <= limit:
            pairs.append((lo, hi))
        k += 1
    return pairs


def solve(text):
    a, b = map(int, text.split()[:2])
    limit = max(a, b)
    cold = _cold_table(limit)
    if (a, b) in cold:
        return 'LOSE'
    # 枚举所有合法着法，取字典序最小且落到必败点者
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 着法合法性：(i,j) 必须是 (i,0) / (0,j) / (i,i) 之一
            if not (i == 0 or j == 0 or i == j):
                continue
            nx, ny = a - i, b - j
            if nx < 0 or ny < 0:
                continue
            if nx == 0 and ny == 0:
                return 'WIN %d %d' % (i, j)
            if (nx, ny) in cold:
                return 'WIN %d %d' % (i, j)
    return 'WIN %d %d' % (a, b)
