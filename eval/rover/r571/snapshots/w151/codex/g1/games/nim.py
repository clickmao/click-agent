def solve(text: str) -> str:
    lines = [l for l in text.splitlines() if l.strip() != ""]
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"
    for idx in range(m):
        target = a[idx] ^ x
        if target < a[idx]:
            return "WIN %d %d" % (idx + 1, a[idx] - target)
    return "LOSE"
