"""Wythoff 博弈: 必败点判定与字典序最小必胜着法。

输入格式:
    一行两个整数 a b (1<=a<=25, 1<=b<=25), 两堆石子数。

玩法: 每次可选
    (i) 从任意一堆取走任意正数目石子;
    (ii) 从两堆同时取走相同的正数目石子。
取走最后一颗者胜。

输出:
    先手必败 => 一行 `LOSE`
    否则     => 一行 `WIN i j`, 从第一堆取 i 颗、第二堆取 j 颗,
                (i,j) 在全部必胜着法中按字典序最小(先比 i 再比 j),
                i,j >= 0 且不同时为 0。
"""


DEAD_ = "LOSE"


def _is_losing(a, b):
    """(a,b) 是否为必败态(轮到行动者必输)。"""
    if a > b:
        a, b = b, a
    # Wythoff 必败点: (floor(k*phi), floor(k*phi^2)), k = b - a
    d = b - a
    k = (d * 5 + 3) // 2  # 近似先给个范围, 实际用精确判定
    # 精确判定: 存在整数 k 使 (a,b) == (floor(k*phi), floor(k*phi^2))
    # 等价于 a == floor(k*phi) 且 b == a + k, 其中 k = b - a
    # floor(k*phi) = k + floor(k/phi) ; phi = (1+sqrt5)/2
    # 用整数运算避免浮点误差: floor(k*phi) = k + floor((k*(sqrt5-1))/2)
    # 这里采用直接整数递推校验: 只需检查 a 是否等于 floor(k*phi)
    kk = d
    # floor(kk*phi) 的精确整数求法: floor((kk*3 + kk*... )) -> 用 isqrt
    from math import isqrt
    # sqrt5 = sqrt(5); floor(k*phi) = (k*3 + k*isqrt5 ... ) 采用:
    # floor(k*phi) = floor((k*(1+sqrt5))/2) = (k + floor(k*sqrt5)) // 2 需要 floor(k*sqrt5)
    # 直接求 floor(k*sqrt5):
    def floor_k_sqrt5(k):
        # 返回 floor(k*sqrt(5)), k>=0
        return isqrt(5 * k * k)

    phi_k = (kk + floor_k_sqrt5(kk)) // 2  # floor(kk*phi)
    return a == phi_k and b == a + kk


def solve(text: str) -> str:
    """入参=完整 stdin 文本, 返回=应当写出的 stdout 文本(末尾不带换行)。"""
    lines = text.split("\n")
    a, b = (int(x) for x in lines[0].split())

    # 枚举所有合法着法, 收集使对手落入必败态的着法, 取字典序最小。
    # 着法按 (i, j) 字典序生成即可保证第一个命中的就是最小。
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # 只能取一堆(另一堆取 0) 或两堆取相同数目
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        return DEAD_
    i, j = best
    return "WIN %d %d" % (i, j)
