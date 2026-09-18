"""多堆 Nim：先手必胜手（堆号最小者）。

输入：第一行 m；第二行 m 个整数。
输出：'WIN p r' 或 'LOSE'，末尾不带换行。
"""


def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    m = int(lines[p].split()[0])
    p += 1
    heaps = []
    while len(heaps) < m and p < len(lines):
        for tok in lines[p].split():
            heaps.append(int(tok))
            if len(heaps) == m:
                break
        p += 1
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            take = heaps[idx] - target
            if take > 0:
                return 'WIN %d %d' % (idx + 1, take)
    return 'LOSE'
