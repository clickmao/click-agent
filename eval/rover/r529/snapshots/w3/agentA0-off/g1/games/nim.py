"""多堆 Nim 必胜手。

输入格式:
    第一行: m      (1<=m<=4 堆数)
    第二行: m 个整数 a1..am (1<=ai<=15 每堆石子数)

玩法: 两人轮流从某一堆取走任意正数目的石子, 取走最后一颗者胜。

输出:
    必胜 -> 一行 "WIN p r" (p = 必胜着法中堆号最小者, 1 起; r = 从该堆取走数)
    必败 -> 一行 "LOSE"
"""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    piles = [int(x) for x in parts[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    # Nim 和为非零时, 必存在堆使其变小到 piles[i]^x; 取堆号最小者。
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN {} {}".format(i + 1, a - target)
    return "LOSE"
