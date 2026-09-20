"""Game: Nim, win/lose and smallest-pile winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for p in sorted(piles):
        target = p ^ x
        if target < p:
            idx = piles.index(p) + 1
            return 'WIN %d %d' % (idx, p - target)
    return 'LOSE'
