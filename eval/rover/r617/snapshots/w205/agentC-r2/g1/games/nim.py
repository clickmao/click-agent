"""多堆 Nim 必胜手。

读入: 第一行一个整数 m (1<=m<=4); 第二行 m 个整数 ai (1<=ai<=15)。
输出: 必胜输出 'WIN p r' (p 为堆号最小者, 从 1 起; r 为从该堆取走数); 必败输出 'LOSE'。末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return 'LOSE'

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
