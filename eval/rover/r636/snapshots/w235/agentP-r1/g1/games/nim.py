"""多堆 Nim: 必胜手。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = a[p] ^ x
        if target < a[p]:
            return 'WIN %d %d' % (p + 1, a[p] - target)
    return 'LOSE'
