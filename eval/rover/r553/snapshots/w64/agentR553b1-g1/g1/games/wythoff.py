"""Wythoff's game: P-positions are a_n = floor(n*phi), b_n = a_n + n."""

PHI = (1.0 + 5 ** 0.5) / 2.0


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])

    # Exact membership test for the lower Wythoff sequence via the
    # Beatty-sequence characterization: n is a lower term iff
    # floor((n + 1) * phi) - floor(n * phi) == 2.
    def is_lower(n):
        if n < 1:
            return False
        return int((n + 1) * PHI) - int(n * PHI) == 2

    def losing(x, y):
        if x > y:
            x, y = y, x
        if x == 0 and y == 0:
            return True
        # y - x == 0 implies not a P-position; phi-based check is exact.
        if y - x <= 0:
            return False
        if not is_lower(y - x):
            return False
        return int((y - x) * PHI) == x

    if losing(a, b):
        return "LOSE"

    # Search all legal moves in lexicographic order (i ascending, then j).
    best_i = best_j = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # simultaneous removal must be equal
            if losing(a - i, b - j):
                best_i, best_j = i, j
                break
        if best_i is not None:
            break
    if best_i is None:
        return "LOSE"
    return "WIN %d %d" % (best_i, best_j)
