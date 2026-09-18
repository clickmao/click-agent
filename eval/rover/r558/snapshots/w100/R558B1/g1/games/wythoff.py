"""Wythoff game."""

MAXN = 40

def _losing(a, b):
    # Grundy-characterization: (a,b) is a P-position iff
    # a == floor(phi*|b-a|) and b == a + |b-a| (Wythoff pairs).
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    phi_n = int(d * ((1 + 5 ** 0.5) / 2.0))
    # correct rounding due to floating error: try nearby values
    for cand in (phi_n - 1, phi_n, phi_n + 1):
        if cand >= 0 and cand == x and cand + d == y:
            return True
    return False


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                # can we take i from pile1 and j from pile2? allowed by rules:
                # (i) from any one pile any positive number; (ii) from both equal number
                # mixed (i>0 and j>0 and i!=j) is NOT allowed
                continue
            if i > 0 and j > 0 and i == j:
                pass
            reach = (a - i, b - j)
            if _losing(reach[0], reach[1]):
                key = (i, j)
                if best is None or key < best:
                    best = key
    if best is None:
        # fallback: search full legal move set
        for i in range(0, a + 1):
            for j in range(0, b + 1):
                if i == 0 and j == 0:
                    continue
                legal = False
                if i > 0 and j == 0:
                    legal = True
                elif i == 0 and j > 0:
                    legal = True
                elif i == j and i > 0:
                    legal = True
                if not legal:
                    continue
                if _losing(a - i, b - j):
                    key = (i, j)
                    if best is None or key < best:
                        best = key
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
