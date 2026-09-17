"""多堆 Nim 必胜手。

solve(text) -> str
  入参 text = 完整 stdin 文本:
    第一行: m (堆数)
    第二行: m 个整数 a1..am (每堆石子数)
  返回: 先手必胜 -> "WIN p r" (p 为堆号最小的必胜着法堆号, r 为取走数);
        否则 "LOSE"。
  原理: nim 和 (异或) 为 0 则必败; 否则找最小的堆 i 使 a_i ^ S < a_i,
        则取走 a_i - (a_i ^ S) 颗。
"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a

    if xor_sum == 0:
        return 'LOSE'

    for idx in range(m):
        a = piles[idx]
        target = a ^ xor_sum
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)

    return 'LOSE'
