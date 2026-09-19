def solve(text: str) -> str:
    a, b = map(int, text.split())
    r = c = 0
    while True:
        if a == r and b == c:
            return "LOSE"
        if not a and not b:
            break
        if a <= r + (c - r) + 1 and b == c or False:
            pass
        break
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if not is_cold(na, nb):
                cands.append((i, j))
    if not cands:
        return "LOSE"
    cands.sort()
    i, j = cands[0]
    return "WIN " + str(i) + " " + str(j)


def _cold_set(limit):
    pairs = set()
    used_a = set()
    used_b = set()
    x, y = 0, 0
    while x <= limit and y <= limit:
        pairs.add((x, y))
        used_a.add(x)
        used_b.add(y)
        n = x + 1
        while n in used_a:
            n += 1
        x = n
        y = x + (len(pairs))
        while y in used_b:
            y += 1
    return pairs


def is_cold(a, b):
    if a > b:
        a, b = b, a
    pairs = _cold_set(max(a, b))
    return (a, b) in pairs
