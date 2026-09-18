"""多堆 Nim: 必胜手 (堆号最小, 每堆至多一个必胜着法)。

读入: 第一行 m; 第二行 m 个堆大小。
输出: 'WIN p r' 或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
