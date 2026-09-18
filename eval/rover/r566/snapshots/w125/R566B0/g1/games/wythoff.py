"""Wythoff's game: LOSE for losing positions, else WIN i j lexicographically smallest."""


_LIMIT = 25


def _losing():
    lose = set()
    for a in range(_LIMIT + 1):
        for b in range(a, _LIMIT + 1):
            # position (a, b) with a <= b is losing if no move reaches a losing position
            ok = True
            # (i) take from one pile
            for i in range(a + 1):
                for j in range(b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0:
                        continue
                    na, nb = a - i, b - j
                    if na > nb:
                        na, nb = nb, na
                    if (na, nb) in lose:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                # (ii) take the same positive number from both piles
                for d in range(1, a + 1):
                    na, nb = a - d, b - d
                    if na <= nb:
                        pass
                    else:
                        na, nb = nb, na
                    if (na, nb) in lose:
                        ok = False
                        break
            if ok:
                lose.add((a, b))
    return lose


def _canon(a, b):
    return (a, b) if a <= b else (b, a)


def solve(text: str) -> str:
    first = text.split()
    a, b = int(first[0]), int(first[1])
    lose = _losing()
    if _canon(a, b) in lose:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _canon(na, nb) in lose:
                return "WIN %d %d" % (i, j)
    return "LOSE"
