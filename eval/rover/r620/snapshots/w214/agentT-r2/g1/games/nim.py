"""多堆 Nim：先手必胜手（堆号最小、对应的取走数目）。

读入: 第一行 m; 第二行 m 个整数 a1..am。
规则: 每次从某一堆取走任意正的数目，取走最后一颗者胜。
输出: 'WIN p r'（p 为堆号最小者，r 为取走数目）或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(t) for t in lines[1].split()[:m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a

    if xor_sum == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        target = a ^ xor_sum  # 希望的剩余量
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
