"""多堆 Nim 必胜手: 输出堆号最小、每堆唯一必胜着法.

stdin: 第一行 m; 第二行 m 个堆大小.
stdout: `WIN p r` 或 `LOSE`.
"""


def _parse(text):
    vals = [ln.split() for ln in text.split("\n") if ln.strip()]
    m = int(vals[0][0])
    piles = [int(x) for x in vals[1][:m]]
    return m, piles


def solve(text):
    m, piles = _parse(text)
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(piles):  # 从堆号最小开始
        target = a ^ x  # 需把该堆变成 target < a
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
