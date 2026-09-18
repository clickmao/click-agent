"""多堆 Nim：最小堆号 + 该堆取走数 的必胜着法。

stdin 首行: m
第二行: m 个整数 a1..am。
输出 'WIN p r' 或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
