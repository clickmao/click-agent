"""多堆 Nim: 输出字典序意义下 (堆号最小) 的必胜手。

输入: 首行 m (堆数); 次行 m 个整数 (每堆石子数)。
每次从某一堆取走任意正数颗, 取走最后一颗者胜。
输出: 必胜 -> "WIN p r" (p 为堆号最小者, r 为取走数); 必败 -> "LOSE"。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = [int(x) for x in lines[idx].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for p in range(1, m + 1):
        a = piles[p - 1]
        target = a ^ x
        if target < a:
            r = a - target
            if r > 0:
                return "WIN %d %d" % (p, r)
    # 理论不可达
    return "LOSE"
