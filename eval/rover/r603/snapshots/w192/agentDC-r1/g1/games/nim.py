"""多堆 Nim: 输出 WIN p r (最小堆号, 每堆至多一个必胜着法) 或 LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return 'LOSE'
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        for tok in lines[idx].split():
            if len(piles) < m:
                piles.append(int(tok))
        idx += 1
    while len(piles) < m:
        piles.append(0)

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - target)
    return 'LOSE'
