"""Wythoff game: output LOSE for cold positions, else lexicographically smallest move."""


def _cold(upper: int):
    """Return set of P-positions (a<=b) up to `upper` via standard recurrence."""
    cold = set()
    seen = set()
    a = 0
    while True:
        while a in seen:
            a += 1
        b = a + a  # placeholder, replaced below
        b = a
        while b in seen or b in (a,) or (a, b) in cold:
            b += 1
        if a > upper:
            break
        cold.add((a, b))
        seen.add(a)
        seen.add(b)
        a += 1
    return cold


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    upper = max(a, b)

    # Enumerate P-positions (a_i, b_i) with both coords <= upper using the rule:
    # a_i = mex of previously used coords, b_i = a_i + i.
    cold = set()
    seen = set()
    i = 0
    while True:
        while i in seen:
            i += 1
        if i > upper:
            break
        j = i + len(cold)  # index of this P-position
        if j > upper:
            break
        cold.add((i, j))
        seen.add(i)
        seen.add(j)

    if (a, b) in cold or (b, a) in cold:
        return "LOSE"

    best = None
    # Option (i): reduce one pile (first pile move i, second pile move j=0 or vice versa).
    for i in range(1, a + 1):
        if (a - i, b) in cold or (b, a - i) in cold:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if (a, b - j) in cold or (b - j, a) in cold:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # Option (ii): remove same positive amount from both piles.
    for d in range(1, min(a, b) + 1):
        if (a - d, b - d) in cold or (b - d, a - d) in cold:
            cand = (d, d)
            if best is None or cand < best:
                best = cand

    return "WIN %d %d" % best
