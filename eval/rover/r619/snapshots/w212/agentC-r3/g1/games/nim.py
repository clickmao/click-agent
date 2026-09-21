"""多堆 Nim: 输出最小堆号的必胜着法。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in heaps:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            return 'WIN %d %d' % (idx + 1, heaps[idx] - target)
    return 'LOSE'
