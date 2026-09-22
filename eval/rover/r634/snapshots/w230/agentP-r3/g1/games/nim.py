def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for p in piles:
        xor ^= p

    if xor == 0:
        return "LOSE"

    best = None
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            cand = (idx + 1, piles[idx] - target)
            if best is None or cand[0] < best[0]:
                best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
