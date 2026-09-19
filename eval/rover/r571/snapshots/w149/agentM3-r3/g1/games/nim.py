"""多堆 Nim: 给出堆号最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    heaps = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(heaps):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
