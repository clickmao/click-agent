"""多堆 Nim 必胜手。

输入格式:
    第一行一个整数 m (1<=m<=4, 石子堆数)
    第二行 m 个整数 a1..am (1<=ai<=15, 每堆石子数)

玩法: 两人轮流进行, 每次从某一堆中取走任意正数目的石子, 取走最后一颗者胜。

输出: 先手有必胜策略时输出一行 `WIN p r` —— p 为必胜着法中堆号最小者 (堆号从 1 开始),
      r 为从该堆取走的石子数 (每堆至多存在一个必胜着法);
      先手必败时输出一行 `LOSE`。
"""


def solve(text: str) -> str:
    """返回 WIN p r 或 LOSE, 末尾不带换行。"""
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a

    if xor_sum == 0:
        return 'LOSE'

    for idx in range(m):
        target = piles[idx] ^ xor_sum
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
