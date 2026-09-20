def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    while lines[idx].strip() == "":
        idx += 1
    piles = [int(t) for t in lines[idx].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN " + str(i + 1) + " " + str(piles[i] - target)
    return "LOSE"
