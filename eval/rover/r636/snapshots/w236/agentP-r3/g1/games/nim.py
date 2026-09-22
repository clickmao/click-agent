"""多堆 Nim：判定先手胜负并给出堆号最小的必胜着法。

入参：完整 stdin 文本；返回：'WIN p r' 或 'LOSE'，末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
