def solve(text):
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].split()
    if not first:
        return ""
    m = int(first[0])
    piles = []
    if len(lines) > 1:
        piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - target)
    return "LOSE"
