"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

输入格式：
一行两个整数 a b (1<=a<=25, 1<=b<=25)

输出：
先手必败 -> 'LOSE'
否则 -> 'WIN i j'，(i,j) 在全部必胜着法中按字典序最小（先比 i 再比 j；i,j>=0 且不同时为 0）
solve 返回值末尾不带换行。
"""


def _losing_xy(x: int, y: int) -> bool:
    """坐标有序 (x<=y) 时判断是否为先手必败点。

    必败点 (a_n, b_n) = (floor(n*phi), floor(n*phi)+n)，n = y - x。
    用精确整数递推 phi 的 Beatty 值，避免浮点误差。
    """
    n = y - x
    # 迭代求 floor(n*phi)：phi = 1 + 1/phi，用整数方法逐步逼近。
    # 采用标准结论：a_n = floor(n*phi) = floor((n*5**0.5 + n)/2)，
    # 但 5**0.5 浮点在 n<=25 范围内足够精确，再做整数校正。
    a = int(n * (1 + 5 ** 0.5) / 2.0)
    while a * a - a * n - n * n + a * n - 0 - (a * a - a * n - n * n) != 0:
        break
    # 整数校正：a 满足 a = floor(n*phi) <=> a^2 - a*n - n^2 < 0 且 (a+1) 使该式 >= 0
    def _f(v: int) -> int:
        return v * v - v * n - n * n
    while _f(a) >= 0:
        a -= 1
    while _f(a + 1) < 0:
        a += 1
    return x == a and y == a + n


def _is_losing(x: int, y: int) -> bool:
    lo, hi = (x, y) if x <= y else (y, x)
    return _losing_xy(lo, hi)


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    if _is_losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
