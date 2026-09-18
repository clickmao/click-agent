def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    a = [int(v) for v in lines[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = a[i] ^ x
        if target < a[i]:
            return "WIN %d %d" % (i + 1, a[i] - target)
    return "LOSE"
