def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
