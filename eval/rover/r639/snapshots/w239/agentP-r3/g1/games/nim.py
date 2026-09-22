"""多堆 Nim：必胜手。

输入格式：第一行 m（堆数）；第二行 m 个整数（各堆石子数）。
每次从某一堆取走任意正数目的石子，取走最后一颗者胜。
输出：先手必胜输出 'WIN p r'（p 为堆号最小的必胜着法所在堆，从 1 开始；
r 为从该堆取走的石子数）；否则输出 'LOSE'。
"""


def solve(text):
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    # 正常情况下不可达
    return 'LOSE'
