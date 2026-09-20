"""Wythoff 博弈: 先手必败点判定 + 字典序最小的必胜着法。

输入: 一行两个整数 a b (1<=a<=25, 1<=b<=25)。
每次可选 (i) 从任意一堆取走任意正数目的石子, 或 (ii) 从两堆同时取走相同的正数目的石子; 取走最后一颗者胜。
输出: 先手必败 'LOSE'; 否则 'WIN i j' (从第一堆取 i 颗、第二堆取 j 颗, 按字典序最小; i,j>=0 且不同时为 0)。
"""


def _is_losing(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    return x == int((y - x) * (1 + 5 ** 0.5) / 2 + 1e-9)


def solve(text: str) -> str:
    nums = list(map(int, text.split()))
    a, b = nums[0], nums[1]

    if _is_losing(a, b):
        return 'LOSE'

    cands = []
    # (i) 只从第一堆取
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            cands.append((i, 0))
    # (i) 只从第二堆取
    for j in range(1, b + 1):
        if _is_losing(a, b - j):
            cands.append((0, j))
    # (ii) 两堆同时取相同数
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            cands.append((t, t))

    i, j = min(cands)
    return 'WIN %d %d' % (i, j)
