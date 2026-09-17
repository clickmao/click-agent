"""nim: 多堆 Nim 必胜手。

输入:
    第一行一个整数 m (1<=m<=4, 石子堆数)
    第二行 m 个整数 a1..am (1<=ai<=15, 每堆石子数)

玩法:
    两人轮流从某一堆中取走任意正数目的石子 (不跨堆, 不超该堆当前石子);
    取走最后一颗石子者胜。

输出:
    先手有必胜策略时输出一行 `WIN p r`
    -- p 为必胜着法中堆号最小者 (从 1 开始), r 为从该堆取走的石子数;
    先手必败时输出一行 `LOSE`。
"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    for p in range(m):
        target = piles[p] ^ xor
        if target < piles[p]:
            return "WIN %d %d" % (p + 1, piles[p] - target)
    return "LOSE"
