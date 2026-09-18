"""多堆 Nim: 最小堆号必胜着法。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = [int(x) for x in lines[idx].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        if piles[i] ^ x < piles[i]:
            take = piles[i] - (piles[i] ^ x)
            return 'WIN ' + str(i + 1) + ' ' + str(take)
    return 'LOSE'
