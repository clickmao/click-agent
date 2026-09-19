def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = x ^ a
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
