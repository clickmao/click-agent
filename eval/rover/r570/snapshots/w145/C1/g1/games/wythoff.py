def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    lim = max(a, b) + 1

    losing = set()
    used = set()
    d = 0
    while True:
        x = d + 1
        while x in used:
            x += 1
        if x > lim:
            break
        y = x + d
        losing.add((x, y))
        losing.add((y, x))
        used.add(x)
        used.add(y)
        d += 1

    if (a, b) in losing:
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                return "WIN %d %d" % (i, j)
    return "LOSE"
