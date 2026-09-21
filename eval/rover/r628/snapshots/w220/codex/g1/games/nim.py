def solve(text: str) -> str:
    data = text.split()
    if not data:
        return ""
    m = int(data[0])
    heaps = [int(x) for x in data[1:1 + m]]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"
    for p in range(m):
        target = heaps[p] ^ x
        if target < heaps[p]:
            return "WIN %d %d" % (p + 1, heaps[p] - target)
    return "LOSE"
