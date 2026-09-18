def solve(text):
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(len(piles)):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
