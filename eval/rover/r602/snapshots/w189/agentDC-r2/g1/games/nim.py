"""多堆 Nim：给出堆号最小者的必胜着法。

solve(text) 入参为完整 stdin 文本，返回应当写出的 stdout 文本（末尾无换行）。

输入格式：
    第一行: m          (1<=m<=4)
    第二行: a1..am     (1<=ai<=15)
玩法：
    每次从某一堆中取走任意正数目石子（不跨堆，不超过该堆现有石子），取走最后一颗者胜。
输出格式：
    先手必胜: 一行 "WIN p r"，p 为堆号最小的必胜着法（堆号自 1 起），r 为从该堆取走数
    先手必败: 一行 "LOSE"
"""
from typing import List


def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
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
