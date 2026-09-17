"""多堆 Nim: 必胜手 (堆号最小, 每堆至多一个必胜着法)。

入参 text: 第一行 "m"; 第二行 m 个整数。
返回: "WIN p r" 或 "LOSE"。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"

    # XOR 归零后: 目标值 target = a_i ^ xor < a_i 的那堆 (唯一)
    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
