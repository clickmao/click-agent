"""多堆 Nim：先手必胜手。

solve(text) 读入首行 m（堆数），第二行 m 个石子数。
必胜输出 "WIN p r"（p 为堆号最小者，r 为从该堆取走的石子数），必败输出 "LOSE"。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m:
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            # 从第 i+1 堆取走 a - target 颗，使异或和归零
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
