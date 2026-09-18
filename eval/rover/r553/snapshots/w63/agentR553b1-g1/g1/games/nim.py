def solve(text):
    lines = text.strip().split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return "WIN %d %d" % (p + 1, piles[p] - target)
