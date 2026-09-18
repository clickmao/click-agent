def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN ' + str(i + 1) + ' ' + str(p - target)
    return 'LOSE'
