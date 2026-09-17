def solve(text):
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"
    for idx in range(m):
        r = a[idx] ^ x
        if r < a[idx]:
            return "WIN " + str(idx + 1) + " " + str(a[idx] - r)
    return "LOSE"
