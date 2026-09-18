def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    LIM = 25
    lose = []
    used_x = set()
    used_y = set()
    n = 0
    while True:
        x = 0
        while x in used_x or x + n in used_y or x in used_y or x + n in used_x:
            x += 1
        y = x + n
        if x > LIM:
            break
        lose.append((x, y))
        used_x.add(x)
        used_y.add(y)
        if x <= LIM and y <= LIM:
            pass
        n += 1
        if n > LIM + 2:
            break
    lose_set = set(lose)
    if (min(a, b), max(a, b)) in {(min(x, y), max(x, y)) for x, y in lose}:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in {(min(x, y), max(x, y)) for x, y in lose}:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
