def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]

    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return "LOSE"

    for pi in range(m):
        target = piles[pi] ^ xor
        if target < piles[pi]:
            return "WIN %d %d" % (pi + 1, piles[pi] - target)
    return "LOSE"
