def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - t)
    return "LOSE"
