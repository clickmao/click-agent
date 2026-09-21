"""多堆 Nim: 必胜手 (堆号最小, 每堆至多一个必胜着法)。

输入: 第一行 m; 第二行 m 个整数 a1..am。
输出: 先手必胜 => 'WIN p r'; 否则 'LOSE'。
"""


def solve(text):
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()][:m]

    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return "LOSE"

    for i in range(m):
        target = piles[i] ^ total
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
