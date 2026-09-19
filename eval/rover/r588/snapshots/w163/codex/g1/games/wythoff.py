def _cold_positions(n):
    cold = {(0, 0)}
    taken = {0}
    i = 1
    while True:
        a = i
        while a in taken:
            a += 1
        b = a + i
        if b > n:
            break
        cold.add((a, b))
        cold.add((b, a))
        taken.add(a)
        taken.add(b)
        i += 1
    return cold


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    cold = _cold_positions(max(a, b))
    if (a, b) in cold:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in cold:
                return "WIN %d %d" % (i, j)
    return "LOSE"
