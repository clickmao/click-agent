def solve(text):
    data = text.split()
    if not data:
        return ""
    idx = 0
    m = int(data[idx]); idx += 1
    piles = []
    for _ in range(m):
        piles.append(int(data[idx])); idx += 1
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    best = None
    for i in range(m):
        target = piles[i] ^ x
        if 0 <= target < piles[i]:
            take = piles[i] - target
            if best is None or i < best[0]:
                best = (i, take)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0] + 1, best[1])
