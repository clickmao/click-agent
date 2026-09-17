def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
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
