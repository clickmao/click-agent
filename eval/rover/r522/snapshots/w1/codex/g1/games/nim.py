def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for p in piles:
        x ^= p

    if x == 0:
        return "LOSE"
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
