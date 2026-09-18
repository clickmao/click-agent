def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"

    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            r = p - target
            return "WIN %d %d" % (idx + 1, r)
    return "LOSE"
