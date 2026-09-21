def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    pile = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in pile:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = pile[i] ^ x
        if t < pile[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(pile[i] - t)
    return 'LOSE'
