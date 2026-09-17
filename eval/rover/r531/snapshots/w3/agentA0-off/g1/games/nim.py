"""多堆 Nim: 必胜时给出堆号最小者的必胜着法（每堆至多一个）。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return 'WIN %d %d' % (i + 1, v - target)
    return 'LOSE'
