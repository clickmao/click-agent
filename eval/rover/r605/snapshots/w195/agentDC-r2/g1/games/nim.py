def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i in range(m):
        t = piles[i] ^ x
        if t < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - t)
    return "LOSE"
