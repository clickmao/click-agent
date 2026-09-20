def solve(text: str) -> str:
    lines = text.strip().split('\n')
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
