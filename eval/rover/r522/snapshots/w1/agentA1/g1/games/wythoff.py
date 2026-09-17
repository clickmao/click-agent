"""Wythoff 博弈: 必败点判定 / 字典序最小必胜着法。

入参 text: 一行 "a b"。
返回: "LOSE" 或 "WIN i j" (i,j>=0, 不同时为 0, 字典序最小)。
"""


def _is_losing(a: int, b: int) -> bool:
    """必败点 = (floor(n*phi), floor(n*phi^2))，两数排序后比对。"""
    lo, hi = (a, b) if a <= b else (b, a)
    # phi = (1+sqrt5)/2; 用整数平方比较避免浮点误差:
    # lo == floor(n*phi) 等价于存在 n 使该式成立; 直接枚举 n 更稳妥。
    n = 0
    while True:
        x = (5 * n * n + 2 * n)  # 判断 n 的候选
        # 逐 n 生成 Beaty 序列, n 上限不超过 max(a,b)
        p = (1 + 5 ** 0.5) / 2
        an = int(n * p)
        bn = an + n
        if an > hi:
            return False
        if an == lo and bn == hi:
            return True
        if an == hi and bn == lo:
            return True
        n += 1


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return "LOSE"

    best = None
    # 着法 (i, j): i 从第一堆取, j 从第二堆取
    # (i) 只取一堆: (i,0) 或 (0,j)
    # (ii) 两堆同取 t: (t,t)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if _is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
