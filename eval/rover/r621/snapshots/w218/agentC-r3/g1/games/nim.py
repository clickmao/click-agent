def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return 'WIN ' + str(idx + 1) + ' ' + str(v - target)
    return 'LOSE'
