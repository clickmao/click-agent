"""多堆 Nim: 求字典序(堆号最小优先)必胜手。

solve(text) 读入: 第一行 m; 第二行 m 个堆大小。
输出 'WIN p r' (p 为堆号, 从 1 开始, 取 r 颗) 或 'LOSE', 末尾不带换行。
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
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
