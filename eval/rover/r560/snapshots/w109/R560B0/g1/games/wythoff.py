def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    x, y = min(a, b), max(a, b)
    phi = (1 + 5 ** 0.5) / 2
    t = int((y - x) * phi)
    lost = False
    for cand in (t - 1, t, t + 1):
        if cand < 0:
            continue
        if int(cand * phi) + cand == x and int((cand + 1) * phi) + cand == y:
            lost = True
            break
    if lost:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            px, py = min(na, nb), max(na, nb)
            tt = int((py - px) * phi)
            is_lost = False
            for cand in (tt - 1, tt, tt + 1):
                if cand < 0:
                    continue
                if int(cand * phi) + cand == px and int((cand + 1) * phi) + cand == py:
                    is_lost = True
                    break
            if is_lost:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
