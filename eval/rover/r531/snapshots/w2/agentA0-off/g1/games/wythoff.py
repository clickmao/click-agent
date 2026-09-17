"""Wythoff 博弈必败点判定。

规则: 每次可从任意一堆取走任意正数石子, 或从两堆同时取走相同正数石子;
      取走最后一颗者胜。
solve(text) 内 text 为完整 stdin 文本:
  一行: a b  (1<=a,b<=25)
返回: 先手必败 -> "LOSE";
      否则 -> "WIN i j" (从第一堆取 i 颗、第二堆取 j 颗, (i,j) 按字典序最小,
      i,j>=0 且不同时为 0)。
"""


def _isqrt(x):
    """整数平方根 floor(sqrt(x)), x>=0, 纯整数运算无浮点误差。"""
    r = int(x ** 0.5)
    while (r + 1) * (r + 1) <= x:
        r += 1
    while r * r > x:
        r -= 1
    return r


def _beatty(d):
    """返回 floor(d * phi), phi=(1+sqrt5)/2。

    推导: floor(d*(1+sqrt5)/2) = (d + floor(d*sqrt5)) // 2。
    """
    s = _isqrt(5 * d * d)
    return (d + s) // 2


def _is_cold(a, b):
    """(a,b) 是否为必败点 (cold position)。

    必败点集合 {(floor(n*phi), floor(n*phi^2))}; 令 lo=min(a,b), hi=max(a,b),
    d=hi-lo, 则必败 <=> floor(d*phi)==lo。
    """
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    return _beatty(d) == lo


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_cold(a, b):
        return "LOSE"
    # 枚举所有合法着法, 取字典序最小 (i 优先, 再 j) 的制胜着法
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # 只允许单堆取或两堆取相同数
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                win_now = True
            else:
                win_now = not _is_cold(na, nb)
            if win_now:
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return "WIN %d %d" % (i, j)
