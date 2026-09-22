"""Wythoff's game: find the lexicographically smallest winning move."""

MAXV = 25

# Winning/losing status for every unordered position (x <= y), 0 <= x,y <= MAXV.
# A position is losing iff it is not the source of any move into a losing
# position; process by increasing total number of stones.
_LOSING = None


def _compute():
    global _LOSING
    if _LOSING is not None:
        return
    lost = [[False] * (MAXV + 1) for _ in range(MAXV + 1)]
    for total in range(MAXV * 2 + 1):
        for x in range(MAXV + 1):
            y = total - x
            if y < x or y > MAXV:
                continue
            # (x, y) is a winning position if it can reach a losing one.
            winning = False
            for j in range(1, y + 1):
                p, q = (x, y - j) if x <= y - j else (y - j, x)
                if lost[p][q]:
                    winning = True
                    break
            if not winning:
                for i in range(1, x + 1):
                    p, q = (x - i, y)
                    if p > q:
                        p, q = q, p
                    if lost[p][q]:
                        winning = True
                        break
            if not winning:
                for t in range(1, x + 1):
                    p, q = x - t, y - t
                    if lost[p][q]:
                        winning = True
                        break
            lost[x][y] = not winning
    _LOSING = lost


def _is_losing(x, y):
    if x > y:
        x, y = y, x
    return _LOSING[x][y]


def solve(text: str) -> str:
    _compute()
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
