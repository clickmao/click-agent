def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])

    limit = max(a, b) + 2
    lose = set()
    for x in range(limit + 1):
        phi = (1 + 5 ** 0.5) / 2
        y = x + int((x * phi) // 1 - x + 0.5)
        lo = x + (x * 0)
        lo = x
        hi = x + int(phi * x + 0.5)
        if hi <= limit:
            lose.add((lo, hi))
            lose.add((hi, lo))
    n = (a, b)
    if n in lose:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                na, nb = a - i, b - j
                if na < 0 or nb < 0:
                    continue
                if (na, nb) in lose:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
