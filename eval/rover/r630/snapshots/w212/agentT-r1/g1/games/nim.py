"""多堆 Nim 必胜手。

输入格式：第一行 ``m``（1<=m<=4 堆数），第二行 m 个整数（1<=ai<=15）。
玩法：两人轮流，每次从某一堆中取走任意正数目的石子（不能跨堆、不超该堆现有
石子），取走最后一颗者胜。
输出：先手必胜输出 ``WIN p r``（p 为必胜着法中堆号最小者，堆号从 1 开始；r 为从
该堆取走的石子数，每堆至多一个必胜着法）；必败输出 ``LOSE``。
"""


def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
