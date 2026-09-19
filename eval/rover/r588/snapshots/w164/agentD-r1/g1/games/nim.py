def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    piles = list(map(int, lines[idx].split()))

    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(len(piles)):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN " + str(i + 1) + " " + str(piles[i] - target)
    return "LOSE"
