def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    a, b = map(int, lines[idx].split())
    moves = []
    # take i from pile1, j from pile2; single-pile or equal-both
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = (i == 0 or j == 0) or (i == j)
            if not ok:
                continue
            moves.append((i, j))
    moves.sort()
    for i, j in moves:
        # resulting position (a-i, b-j) should be a losing position
        na, nb = a - i, b - j
        if na > nb:
            na, nb = nb, na
        # losing iff na == int((nb-na)*phi)
        d = nb - na
        t = int(d * 0.6180339887498949) + 1
        loser = False
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and cand == na:
                loser = True
                break
        # more robust: check candidate x with floor(x*phi)==d
        if not loser and d >= 0:
            x = 0
            while x * 1.6180339887498949 < d:
                x += 1
            for cand in (x - 1, x, x + 1):
                if cand >= 0 and cand == na and int(cand * 1.6180339887498949) == d:
                    loser = True
                    break
        if loser:
            return "WIN %d %d" % (i, j)
    return "LOSE"
