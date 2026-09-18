def _losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5)) / 2.0
        k = int(p)
        if k >= 1 and i == y - x and y == k + i:
            return True
        if k + i > y:
            return False
        i += 1

def solve(text):
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].split()
    if len(first) < 2:
        return ""
    a = int(first[0])
    b = int(first[1])
    if _losing(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni = a - i
            nj = b - j
            if ni > nj:
                ni, nj = nj, ni
            if not _losing(a - i, b - j):
                continue
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
