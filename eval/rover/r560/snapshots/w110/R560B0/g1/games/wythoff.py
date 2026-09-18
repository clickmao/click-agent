def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    losing = set()
    seen_a = set()
    seen_b = set()
    for i in range(0, 30):
        if i in seen_a:
            continue
        j = i + i // 2 + 1
        if j in seen_b:
            continue
        seen_a.add(i)
        seen_b.add(j)
        losing.add((i, j))
        losing.add((j, i))
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            if (na, nb) in losing and (best is None or (i, j) < best):
                best = (i, j)
    return "WIN %d %d" % best
