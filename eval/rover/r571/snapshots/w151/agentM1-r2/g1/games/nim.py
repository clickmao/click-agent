def solve(text):
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    pile = list(map(int, lines[1].split()))[:m]

    x = 0
    for a in pile:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        target = pile[idx] ^ x
        if target < pile[idx]:
            return "WIN %d %d" % (idx + 1, pile[idx] - target)
