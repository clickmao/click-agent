def solve(text: str) -> str:
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split())
    LIM = 60
    lose = set()
    for x in range(LIM + 1):
        for y in range(LIM + 1):
            if x == 0 and y == 0:
                lose.add((0, 0))
                continue
            ok = False
            for d in range(1, x + 1):
                if (x - d, y) in lose:
                    ok = True
                    break
            if not ok:
                for d in range(1, y + 1):
                    if (x, y - d) in lose:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(x, y) + 1):
                    if (x - d, y - d) in lose:
                        ok = True
                        break
            if not ok:
                lose.add((x, y))
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            legal = False
            if i > 0 and j == 0:
                legal = True
            elif i == 0 and j > 0:
                legal = True
            elif i > 0 and j > 0 and i == j:
                legal = True
            if legal and (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
