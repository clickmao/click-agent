"""多堆 Nim 必胜手。

输入格式 (完整 stdin 文本):
    第一行一个整数 m  (1<=m<=4 石子堆数)
    第二行 m 个整数 a1..am (1<=ai<=15 每堆石子数)

玩法: 每次从某一堆中取走任意正数目的石子 (不跨堆, 不超该堆现有数), 取走最后一颗者胜。

输出:
    先手必胜 -> 一行 "WIN p r"  (p 为必胜着法中堆号最小者, 堆号从 1 开始;
                                 r 为从该堆取走的石子数; 每堆至多一个必胜着法)
    先手必败 -> 一行 "LOSE"
"""

from typing import List


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (末尾不带换行)。"""
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles: List[int] = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    # p 取堆号最小的可行动堆, r = a - (a ^ x)  (>0 当且仅当该堆是必胜着法所在)
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
