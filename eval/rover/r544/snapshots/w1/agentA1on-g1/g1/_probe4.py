import games.wythoff as w
from math import isqrt


def cold_solver(limit):
    """Independent cold-set construction by mex (no closed form)."""
    used = set()
    cold = []
    lo = 0
    while True:
        while lo in used:
            lo += 1
        hi = lo + 1
        while hi in used:
            hi += 1
        if hi > limit:
            break
        cold.append((lo, hi))
        if lo != hi:
            cold.append((min(lo, hi), max(lo, hi)))
        used.add(lo)
        used.add(hi)
        lo += 1
    return set(cold)


ref = cold_solver(25)
print("mex cold:", sorted(ref))
print("diff:", sorted(w._COLD ^ ref))
