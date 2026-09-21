"""多堆 Nim：判定先手胜负并给出堆号最小的必胜着法。

入参 text: 第一行 "m"；第二行 m 个整数 a1..am。
返回: "WIN p r" 或 "LOSE"，末尾不带换行。
约定: 每次从某一堆取走任意正数目石子，取走最后一颗者胜。
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
