"""多堆 Nim: 输出堆号最小的必胜着法。

stdin: 首行 "m"; 第二行 m 个堆大小。
stdout: "WIN p r" 或 "LOSE", 末尾不带换行。
"""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
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
