"""多堆 Nim：给最小堆号的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (idx + 1, p - target)
    return 'LOSE'
