"""多堆 Nim: 先手必胜手(WIN p r)或 LOSE。

标准结论: XOR 为 0 则必败; 否则对堆 p, 新值 a_p' = a_p ^ xor,
取走 r = a_p - a_p' > 0 即为必胜着法。要求堆号最小者。
"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(data[1 + i]) for i in range(m)]

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
