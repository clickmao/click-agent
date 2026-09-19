"""Multi-pile Nim: winning move with smallest pile index."""


def solve(text):
    lines = text.split('\n')
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            take = piles[idx] - target
            return 'WIN ' + str(idx + 1) + ' ' + str(take)
    return 'LOSE'
