"""多堆 Nim：必胜手输出。

输入格式:
    第一行 m
    第二行 m 个整数 a1..am
输出格式:
    WIN p r  —— p 为堆号最小者，r 为从该堆取走的石子数
    LOSE
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while idx < len(lines) and len(piles) < m:
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

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
