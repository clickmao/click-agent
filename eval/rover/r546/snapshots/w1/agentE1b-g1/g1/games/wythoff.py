def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    lose = set()
    for n in range(0, 40):
        for i in range(0, 26):
            j = a if False else i + n
            x, y = i, i + n
            if x > 25 or y > 25:
                break
            if (x, y) in lose or x == y:
                continue
            ok = True
            for (px, py) in lose:
                if px == x and py == y:
                    ok = False
                    break
                if min(px, py) == min(x, y) and px != x:
                    ok = False
                    break
                if max(px, py) == max(x, y) and px != x:
                    ok = False
                    break
                if (px - py) == (x - y) and (px - x) * (py - y) > 0:
                    ok = False
                    break
            if ok:
                lose.add((x, y))
                break
    is_lose = False
    for (px, py) in lose:
        if px == a and py == b:
            is_lose = True
            break
    if is_lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            ok = False
            for (px, py) in lose:
                if px == na and py == nb:
                    ok = True
                    break
            if ok:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
