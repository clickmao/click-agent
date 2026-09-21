LOSE_SET = set()


def _build():
    if LOSE_SET:
        return
    for a in range(1, 31):
        for b in range(1, 31):
            if _is_lose(a, b):
                LOSE_SET.add((a, b))


def _is_lose(a, b):
    for s in range(1, min(a, b) + 1):
        if (a - s, b - s) in LOSE_SET:
            return False
    for i in range(1, a + 1):
        if (a - i, b) in LOSE_SET:
            return False
    for j in range(1, b + 1):
        if (a, b - j) in LOSE_SET:
            return False
    return True


def _wins(a, b):
    res = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in LOSE_SET:
                res.append((i, j))
    res.sort()
    return res


def solve(text):
    LOSE_SET.clear()
    for a in range(0, 33):
        for b in range(0, 33):
            lose = True
            for s in range(1, min(a, b) + 1):
                if (a - s, b - s) in LOSE_SET:
                    lose = False
                    break
            if lose:
                for i in range(1, a + 1):
                    if (a - i, b) in LOSE_SET:
                        lose = False
                        break
            if lose:
                for j in range(1, b + 1):
                    if (a, b - j) in LOSE_SET:
                        lose = False
                        break
            if lose:
                LOSE_SET.add((a, b))
    data = text.split()
    if not data:
        return ""
    a = int(data[0])
    b = int(data[1])
    if (a, b) in LOSE_SET:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in LOSE_SET:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0], best[1])
