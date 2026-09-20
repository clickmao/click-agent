def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    piles = None
    j = idx + 1
    while j < len(lines):
        parts = lines[j].split()
        if len(parts) >= m:
            try:
                piles = [int(x) for x in parts[:m]]
                break
            except ValueError:
                j += 1
                continue
        j += 1
    if piles is None:
        piles = []

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return "WIN " + str(i + 1) + " " + str(take)
    return "LOSE"
