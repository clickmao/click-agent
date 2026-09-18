"""多堆 Nim：必胜手（堆号最小优先）。

读入: 第一行 m; 第二行 m 个整数 a1..am。
输出: 必胜 => 'WIN p r' (p 为堆号最小的必胜着法所在堆, r 为取走数); 必败 => 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    m = int(first[0])
    piles = [int(x) for x in lines[1].split()]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    for idx in range(1, m + 1):
        a = piles[idx - 1]
        target = a ^ x
        if target < a:
            return "WIN " + str(idx) + " " + str(a - target)
    return "LOSE"
