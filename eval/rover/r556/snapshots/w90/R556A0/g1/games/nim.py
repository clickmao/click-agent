def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        need = a ^ x
        if need < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - need)
    return 'LOSE'
