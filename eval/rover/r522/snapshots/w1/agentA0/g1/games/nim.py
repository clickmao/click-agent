"""Multi-pile Nim: winning move is smallest pile index with nonzero xor reduction."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return 'LOSE'

    for idx in range(m):
        # target pile value so that xor becomes 0: piles[idx] -> piles[idx] ^ x
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
