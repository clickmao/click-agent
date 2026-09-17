"""Wythoff 博弈必败点判定。

输入文本 (stdin 全部):
    一行两个整数 a b (1<=a<=25, 1<=b<=25)

玩法: 每次可选 (i) 从任意一堆取走任意正数目, 或 (ii) 从两堆同时取走相同正数目;
      取走最后一颗石子者胜。
输出: 先手必败 -> 一行 `LOSE`; 否则一行 `WIN i j`, 表示从第一堆取 i 颗、第二堆取 j 颗,
      且 (i, j) 在全部必胜着法中按字典序最小 (先比 i 再比 j; i,j>=0 且不同时为 0)。
末尾不带换行。
"""


def _is_losing(a, b):
    """Wythoff 必败态 (P-position): 排序后满足 b-a = d 且 a == floor(d*phi)。"""
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    d = b - a
    # floor(d * golden_ratio), 用整数运算避免浮点误差
    # golden_ratio = (1+sqrt(5))/2; floor(d*phi) = floor((d + d*sqrt(5))/2)
    import math
    x = (d + int(math.isqrt(5 * d * d))) // 2
    return a == x


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return 'LOSE'

    # 枚举所有合法着法, 取字典序最小 (先 i 后 j) 的必胜着法
    # 着法 (i, j): 从第一堆取 i, 第二堆取 j, 0<=i<=a, 0<=j<=b, i+j>0
    # 合法: 单堆取(i>0,j==0 或 i==0,j>0) 或 同时同数(i==j>0)
    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法性: 单堆取 或 两堆等量取
            legal = (j == 0) or (i == 0) or (i == j)
            if not legal:
                continue
            if _is_losing(a - i, b - j):
                candidates.append((i, j))
    # 候选已按 i 升序、j 升序枚举, 直接取第一个
    i, j = candidates[0]
    return 'WIN {} {}'.format(i, j)
