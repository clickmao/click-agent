"""多堆 Nim: 输出堆号最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = piles[i] ^ x
        if t < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - t)
    return 'LOSE'
