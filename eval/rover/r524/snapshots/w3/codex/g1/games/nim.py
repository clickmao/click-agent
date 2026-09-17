def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx, p in enumerate(piles, 1):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (idx, p - target)
    return "LOSE"
