def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN " + str(idx + 1) + " " + str(p - target)
    return "LOSE"
