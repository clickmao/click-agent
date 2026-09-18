def _is_lose(a, b):
    # Wythoff P-positions: (floor(k*phi), floor(k*phi^2))
    if a > b:
        a, b = b, a
    k = (int(((1 + 5 ** 0.5) / 2) * a))
    for kk in (k - 1, k, k + 1):
        if kk >= 0:
            t = int(kk * ((1 + 5 ** 0.5) / 2))
            u = t + kk
            if (t, u) == (a, b):
                return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_lose(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
