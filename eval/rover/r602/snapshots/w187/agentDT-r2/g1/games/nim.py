"""Nim (multi-pile): smallest-pile winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    m = int(tokens[pos]); pos += 1
    piles = [int(tokens[pos + i]) for i in range(m)]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ xor
        if target < piles[i]:
            r = piles[i] - target
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'
