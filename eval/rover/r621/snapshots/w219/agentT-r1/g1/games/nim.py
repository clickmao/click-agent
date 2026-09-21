"""多堆 Nim: 给出堆号最小的必胜着法。

输入文本格式:
    第一行: m
    第二行: m 个整数 a1..am
输出: 'WIN p r' 或 'LOSE', 末尾不带换行。
"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return "WIN " + str(p + 1) + " " + str(piles[p] - target)
    return "LOSE"
