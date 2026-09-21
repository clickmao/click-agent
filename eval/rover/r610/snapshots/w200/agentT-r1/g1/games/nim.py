"""nim: 多堆 Nim 的必胜手。

输入格式：
    第一行 m（堆数）
    第二行 m 个整数 a1..am（每堆石子数）
输出：WIN p r（堆号最小者，从该堆取走石子数 r）或 LOSE。
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

    for idx in range(m):
        rest = 0
        for j in range(m):
            if j != idx:
                rest ^= piles[j]
        if rest < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - rest)
    return "LOSE"
