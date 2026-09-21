def solve(text: str) -> str:
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i in range(m):
        t = piles[i] ^ x
        if t < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - t)
    return "LOSE"
