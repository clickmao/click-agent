def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return "LOSE"
    for i, p in enumerate(piles):
        target = p ^ xor
        if target < p:
            return "WIN " + str(i + 1) + " " + str(p - target)
    return "LOSE"
