"""多堆 Nim：堆号最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    a = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = a[idx] ^ x
        if target < a[idx]:
            return 'WIN %d %d' % (idx + 1, a[idx] - target)
    return 'LOSE'
