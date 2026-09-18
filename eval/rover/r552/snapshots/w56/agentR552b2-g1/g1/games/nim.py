def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for i, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return "WIN %d %d" % (i + 1, v - target)
    return "LOSE"
