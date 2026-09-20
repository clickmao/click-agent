def solve(text):
    lines = text.split("\n")
    m = int(lines[0])
    a = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"
    for p in range(m):
        t = a[p] ^ x
        if t < a[p]:
            return "WIN " + str(p + 1) + " " + str(a[p] - t)
    return "LOSE"
