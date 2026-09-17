def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    total = 0
    for p in piles:
        total ^= p
    if total == 0:
        return "LOSE"
    for i, p in enumerate(piles):
        target = p ^ total
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
