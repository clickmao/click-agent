def _losing(p, q):
    if p > q:
        p, q = q, p
    d = q - p
    # losing positions are (floor(d*phi), floor(d*phi)+d), phi=(1+sqrt5)/2.
    # Find n = floor(d*phi) by integer search: n is the largest integer with
    # (2n - d)^2 <= 5*d^2 and 2n >= d.
    n = d
    while (2 * (n + 1) - d) ** 2 <= 5 * d * d:
        n += 1
    return p == n


def solve(text: str) -> str:
    a, b = map(int, text.split())

    if _losing(a, b):
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
