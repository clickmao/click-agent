"""Wythoff game: cold-position test and lexicographically smallest winning move."""


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    def losing(x, y):
        # Grundy-based cold positions: (floor(m*phi), floor(m*phi^2))
        def is_cold(u, v):
            if u > v:
                u, v = v, u
            # check whether (u, v) is a Wythoff pair
            m = v - u
            if m < 0:
                return False
            import math
            phi = (1 + 5 ** 0.5) / 2
            cand_u = int(m * phi)
            for cu in (cand_u - 2, cand_u - 1, cand_u, cand_u + 1, cand_u + 2):
                if cu < 0:
                    continue
                cv = cu + m
                if cu == u and cv == v:
                    return True
            return False

        return is_cold(x, y)

    if losing(a, b):
        return "LOSE"

    best = None
    # move (i) take i from first pile
    for i in range(1, a + 1):
        if losing(a - i, b):
            best = (i, 0)
            break
    if best is None:
        # move (i) take j from second pile
        for j in range(1, b + 1):
            if losing(a, b - j):
                best = (0, j)
                break
    if best is None:
        # move (ii) take t from both
        for t in range(1, min(a, b) + 1):
            if losing(a - t, b - t):
                best = (t, t)
                break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
