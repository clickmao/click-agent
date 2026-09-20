"""Nim: multi-pile last-stone-wins, minimal pile-index winning move.

stdin format:
  line 1: m  (1<=m<=4 piles)
  line 2: m pile sizes (1<=ai<=15)
Output: 'WIN p r' (smallest pile index p, stones r removed) or 'LOSE'.
"""



def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
