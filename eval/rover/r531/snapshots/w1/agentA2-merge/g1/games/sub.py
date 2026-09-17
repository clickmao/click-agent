"""取石子子游戏 (减法博弈)。

输入格式 (完整 stdin 文本):
    第一行两个整数 n k  (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
    第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 保证含 1)

玩法: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。

输出:
    先手必胜 -> 一行 "WIN m"  (m 为数值最小的必胜首取数)
    先手必败 -> 一行 "LOSE"
"""

from typing import List


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (末尾不带换行)。"""
    lines = [ln for ln in text.split("\n")]
    n, k = (int(x) for x in lines[0].split())
    steps: List[int] = [int(x) for x in lines[1].split()][:k]

    # win[i] = 剩余 i 颗时轮到行动的一方是否必胜 (先手记 win)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        can = False
        for s in steps:
            if s <= i and not win[i - s]:
                can = True
                break
        win[i] = can

    if not win[n]:
        return "LOSE"

    # 数值最小的必胜首取数: 取 s 后对手处于必败态
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
