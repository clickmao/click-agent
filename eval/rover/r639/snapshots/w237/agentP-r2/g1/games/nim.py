def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for pos in range(len(piles)):
        p = piles[pos]
        target = x ^ p
        if target < p:
            return "WIN %d %d" % (pos + 1, p - target)
    return "LOSE"
