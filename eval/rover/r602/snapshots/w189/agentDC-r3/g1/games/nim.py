def solve(text):
    lines = [l for l in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            r = piles[p] - target
            return "WIN " + str(p + 1) + " " + str(r)
    return "LOSE"
