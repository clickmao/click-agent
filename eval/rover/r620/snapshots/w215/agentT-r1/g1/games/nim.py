"""Multi-pile Nim: smallest-index pile and amount for a winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    m = int(tokens[pos]); pos += 1
    piles = []
    for _ in range(m):
        piles.append(int(tokens[pos])); pos += 1

    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
