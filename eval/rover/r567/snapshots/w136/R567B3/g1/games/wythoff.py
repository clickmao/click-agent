def solve(text: str) -> str:
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    was_swapped = a != b and False
    # recompute original order flag
    orig_a, orig_b = map(int, text.split())
    swapped = orig_a > orig_b
    # P-positions of Wythoff: (floor(m*phi), floor(m*phi^2))
    import math
    phi = (1 + math.sqrt(5)) / 2
    p_positions = set()
    m = 0
    while True:
        x = int(math.floor(m * phi))
        y = int(math.floor(m * phi * phi))
        if x > 25 and y > 25:
            break
        p_positions.add((x, y))
        p_positions.add((y, x))
        m += 1
    if (orig_a, orig_b) in p_positions:
        return "LOSE"
    best = None
    for i in range(0, orig_a + 1):
        for j in range(0, orig_b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (orig_a - i, orig_b - j) in p_positions:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
