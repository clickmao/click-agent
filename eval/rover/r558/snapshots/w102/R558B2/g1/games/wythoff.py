def solve(text):
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    lost = set()
    for x in range(0, a + 1):
        for y in range(x, b + 1):
            is_lost = True
            for i in range(0, x + 1):
                for j in range(i, y + 1):
                    if i == 0 and j == 0:
                        continue
                    single = (i == 0 and j == y) or (j == i and x - i == 0)
                    pair = (i == j and i > 0)
                    if single or pair:
                        if (x - i, y - j) in lost:
                            is_lost = False
                            break
                if not is_lost:
                    break
            if is_lost:
                lost.add((x, y))
    if (a, b) in lost:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j or i == 0 or j == 0:
                na, nb = a - i, b - j
                if na > nb:
                    na, nb = nb, na
                if (na, nb) in lost:
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN %d %d' % best
