def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - t)
    return 'LOSE'
