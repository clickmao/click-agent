"""Wythoff game: lexicographically smallest winning move or LOSE."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    parts = lines[idx].split()
    a, b = int(parts[0]), int(parts[1])

    # P-positions (losing for mover): (floor(n*phi), floor(n*phi^2))
    losing = set()
    n = 0
    while True:
        x = (n * 1618033988749894848204586834365638117720309179805762862135448622705260462818902442668243613920523549206) // 10 ** 100
        x = int(n * 1.6180339887498948482)
        y = x + n
        if x > 25 and y > 25:
            break
        if x <= 25 and y <= 25:
            losing.add((x, y))
        n += 1
        if n > 100:
            break

    if a > b:
        key = (b, a)
    else:
        key = (a, b)
    if key in losing:
        return "LOSE"

    best = None
    # move (i, 0): take i from pile one
    for i in range(0, a + 1):
        if i == 0:
            continue
        na, nb = a - i, b
        key2 = (na, nb) if na <= nb else (nb, na)
        if key2 in losing:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # move (0, j)
    for j in range(1, b + 1):
        na, nb = a, b - j
        key2 = (na, nb) if na <= nb else (nb, na)
        if key2 in losing:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # move (i, i)
    for i in range(1, min(a, b) + 1):
        na, nb = a - i, b - i
        key2 = (na, nb) if na <= nb else (nb, na)
        if key2 in losing:
            cand = (i, i)
            if best is None or cand < best:
                best = cand

    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0], best[1])
