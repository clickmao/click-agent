def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for p in piles:
        x ^= p

    if x == 0:
        return "LOSE"

    for i, p in enumerate(piles):
        r = p ^ x
        if r < p:
            return "WIN %d %d" % (i + 1, p - r)
    return "LOSE"
