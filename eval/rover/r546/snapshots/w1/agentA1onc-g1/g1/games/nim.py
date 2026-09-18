"""多堆 Nim 必胜手。

solve(text) 读入:
  第一行 m (1<=m<=4 堆数)
  第二行 m 个整数 a1..am (每堆石子数)
规则: 每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
输出: 先手必胜 -> 'WIN p r' (p 为堆号最小者的必胜着法, r 为取走数目);
      先手必败 -> 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor_all = 0
    for a in piles:
        xor_all ^= a

    if xor_all == 0:
        return 'LOSE'

    # 堆号最小且存在必胜着法: 取 r 后该堆变 b, 使 xor' = 0
    for idx in range(m):
        a = piles[idx]
        b = a ^ xor_all
        if b < a:
            r = a - b
            return 'WIN %d %d' % (idx + 1, r)
    return 'LOSE'
