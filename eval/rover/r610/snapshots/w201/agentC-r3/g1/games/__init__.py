def wythoff_cold(limit):
    """Return cold (P-position) pairs (x, y) with x <= y up to pairs used, plus the used set."""
    used = set()
    cold = set()
    n = 0
    while len(cold) < limit:
        if n not in used:
            m = n + 1
            while m in used:
                m += 1
            used.add(n)
            used.add(m)
            cold.add((n, m))
        n += 1
    return cold, used
