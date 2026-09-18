"""多堆 Nim: 输出最小堆号的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
