def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split())

    losing = set()
    seen_y = set()
    i = 0
    while True:
        x = int(i * 1.618033988749895)
        if x < i:
            x = i
        while x in seen_y or x - i in seen_y:
            x += 1
        y = x + i
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        seen_y.add(x)
        seen_y.add(y)
        i += 1

    def is_lose(p, q):
        if p > q:
            p, q = q, p
        return (p, q) in losing

    if is_lose(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if is_lose(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
