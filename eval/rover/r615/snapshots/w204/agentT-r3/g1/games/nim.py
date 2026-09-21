def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for i in range(m):
        t = piles[i] ^ xor
        if t < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - t)
    return "LOSE"
