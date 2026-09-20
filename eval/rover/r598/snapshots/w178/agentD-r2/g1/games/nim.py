def solve(text: str) -> str:
    data = text.split()
    idx = 0
    m = int(data[idx]); idx += 1
    piles = [int(data[idx + i]) for i in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN " + str(i + 1) + " " + str(piles[i] - target)
    return "LOSE"
