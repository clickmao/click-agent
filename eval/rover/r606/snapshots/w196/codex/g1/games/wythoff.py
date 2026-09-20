MAX = 26


def _losing():
    lose = set()
    for a in range(MAX):
        for b in range(MAX):
            ok = False
            for i in range(1, a + 1):
                if (a - i, b) in lose:
                    ok = True
                    break
            if not ok:
                for j in range(1, b + 1):
                    if (a, b - j) in lose:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(a, b) + 1):
                    if (a - t, b - t) in lose:
                        ok = True
                        break
            if not ok:
                lose.add((a, b))
    return lose


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lose = _losing()
    if (a, b) in lose:
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if (a - i, b - j) in lose:
                return "WIN %d %d" % (i, j)
    return "LOSE"
