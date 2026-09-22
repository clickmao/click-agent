PHI = (1 + 5 ** 0.5) / 2.0


def _pair(ax):
    # Wythoff 必败点 (cold positions): (floor(n*phi), floor(n*phi^2))
    a = int(ax * PHI)
    return (a, a + ax)


def _is_losing(u, v):
    if u > v:
        u, v = v, u
    d = v - u
    n = int(d / (PHI * PHI))
    for cand in range(max(0, n - 3), n + 4):
        if _pair(cand) == (u, v):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _is_losing(a, b):
        return "LOSE"
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            moves.append((i, j))
    moves.sort()
    for i, j in moves:
        if _is_losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
