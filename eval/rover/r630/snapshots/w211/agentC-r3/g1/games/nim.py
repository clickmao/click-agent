def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(len(piles)):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return "WIN " + str(i + 1) + " " + str(take)
    return "LOSE"
