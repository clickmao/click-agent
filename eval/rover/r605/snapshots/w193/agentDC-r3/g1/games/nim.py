"""多堆 Nim 必胜手: 输出堆号最小的必胜着法。

输入: 第一行 m (1<=m<=4); 第二行 m 个整数 a1..am (1<=ai<=15)。
每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
输出: 先手必胜时 'WIN p r' (p 为必胜着法中堆号最小者, 堆号从 1 开始; r 为取走数); 否则 'LOSE'。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != '']
    idx = 0
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    idx += 1

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i, a - target)
    return 'LOSE'
