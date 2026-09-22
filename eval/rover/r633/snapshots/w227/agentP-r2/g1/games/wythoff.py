def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                moves.append((i, j))
    moves.sort()
    for i, j in moves:
        na, nb = a - i, b - j
        if (na, nb) not in LOSE_SET:
            return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _cold_squares(limit):
    res = set()
    used = set()
    x = 0
    while True:
        y = x + 0
        while True:
            if x > limit and y > limit:
                return res
            if x not in used and y not in used and x != y:
                res.add((x, y))
                res.add((y, x))
                used.add(x)
                used.add(y)
                break
            y += 1
        x += 1


LOSE_SET = frozenset(_cold_squares(30))
