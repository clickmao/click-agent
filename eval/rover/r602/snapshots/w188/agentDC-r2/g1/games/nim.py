"""多堆 Nim: 输出堆号最小的必胜着法。

读入: 第一行一个整数 m (1<=m<=4 堆数); 第二行 m 个整数 a1..am (1<=ai<=15)。
玩法: 每次从某一堆取走任意正数目 (不超该堆现有), 取走最后一颗者胜。
输出: 先手必胜时输出 'WIN p r' —— p 为必胜着法中堆号最小者 (从 1 开始),
      r 为从该堆取走的石子数 (每堆至多存在一个必胜着法); 否则输出 'LOSE'。
"""


def solve(text: str) -> str:
    ints = text.split()
    m = int(ints[0])
    piles = [int(x) for x in ints[1:1 + m]]

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
