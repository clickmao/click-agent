def _lose_set(limit: int):
    a = []
    b = []
    used = set()
    k = 0
    while True:
        m = int(k * ((5 ** 0.5) + 1) / 2)
        while m in used:
            m += 1
        n2 = m + k
        if m > limit and n2 > limit:
            break
        a.append(m)
        b.append(n2)
        used.add(m)
        used.add(n2)
        k += 1
    return a, b


def _is_lose(x, y):
    if x > y:
        x, y = y, x
    a, b = _lose_set(max(x, y) + 2)
    for i in range(len(a)):
        if a[i] == x and b[i] == y:
            return True
    return False


def solve(text: str) -> str:
    lines = text.splitlines()
    x, y = map(int, lines[0].split())
    if _is_lose(x, y):
        return "LOSE"
    best = None
    for i in range(0, x + 1):
        for j in range(0, y + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_lose(x - i, y - j):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
