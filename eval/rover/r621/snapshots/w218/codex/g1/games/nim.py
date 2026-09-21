def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    heaps = [int(x) for x in data[1:1 + m]]

    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"

    for i, a in enumerate(heaps):
        want = a ^ x
        if want < a:
            return "WIN %d %d" % (i + 1, a - want)
    return "LOSE"
