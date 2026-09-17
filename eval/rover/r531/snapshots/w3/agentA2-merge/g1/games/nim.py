"""多堆 Nim：输出最小堆号的必胜着法 `WIN p r`，否则 `LOSE`。"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a
    if xor_sum == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        target = a ^ xor_sum  # 留 target 颗可使异或和为 0
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    # 理论上不可达（异或和非零必有解）
    return "LOSE"
