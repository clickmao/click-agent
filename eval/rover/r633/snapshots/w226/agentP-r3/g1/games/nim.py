"""多堆 Nim: 必胜时给出堆号最小的必胜着法 (堆号从 1 开始)。

stdin 规格: 第一行 m; 第二行 m 个整数 a1..am。
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

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
