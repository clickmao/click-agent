import sys


def cold(a, b):
    if a > b:
        a, b = b, a
    t = int((b - a) * ((5.0 ** 0.5 + 1.0) / 2.0))
    for cand in (t - 1, t, t + 1):
        if cand >= 0:
            ca = int(cand * ((5.0 ** 0.5 + 1.0) / 2.0))
            cb = ca + cand
            if ca == a and cb == b:
                return True
    return False


def solve(text):
    a, b = map(int, text.split()[:2])
    if cold(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            if i > 0 and j > 0 and i > a - 0:
                continue
            if i > 0 and j > 0 and i > a:
                continue
            if i > 0 and j > 0 and j > b:
                continue
            if (i > 0 and j > 0 and i == j) or (i > 0 and j == 0) or (i == 0 and j > 0):
                na, nb = a - i, b - j
                if na < 0 or nb < 0:
                    continue
                if cold(na, nb):
                    best = (i, j)
                    break
        if best is not None:
            break
    return "WIN %d %d" % best


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
