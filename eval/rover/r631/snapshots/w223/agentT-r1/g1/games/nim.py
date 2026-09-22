def solve(text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip() != ""]
    m = int(lines[0].split()[0])
    heaps = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in heaps:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = heaps[i] ^ x
        if target < heaps[i]:
            return "WIN %d %d" % (i + 1, heaps[i] - target)
    return "LOSE"
