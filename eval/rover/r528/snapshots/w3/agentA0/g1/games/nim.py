"""Multi-pile Nim: take any positive number from one pile; last stone wins.

Input: m / a1 .. am.
Output: 'WIN p r' (smallest pile index among winning moves, stones removed) or 'LOSE'.
"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        # want piles[idx] -> piles[idx] ^ x  (reduce, never increase)
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
