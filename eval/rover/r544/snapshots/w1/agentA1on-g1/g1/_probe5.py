import games.wythoff as w
from functools import lru_cache


@lru_cache(maxsize=None)
def cold(a, b):
    """True iff (a,b) is a P-position under the real move rules."""
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    for i in range(1, a + 1):
        if cold(a - i, b):
            return False
    for j in range(1, b + 1):
        if cold(a, b - j):
            return False
    for t in range(1, min(a, b) + 1):
        if cold(a - t, b - t):
            return False
    return True


ref = {(a, b) for a in range(26) for b in range(26) if a <= b and cold(a, b)}
ref_norm = {(a, b) for (a, b) in ref}
mine = set(w._COLD) | {(0, 0)}
print("recursive cold:", sorted(ref))
print("closed-form cold:", sorted(mine))
print("only in ref:", sorted(ref - mine))
print("only mine:", sorted(mine - ref))

missing = []
for a in range(1, 26):
    for b in range(1, 26):
        if not cold(a, b):
            lo, hi = (a, b) if a <= b else (b, a)
            found = None
            for i in range(lo + 1):
                for j in range(hi + 1):
                    if i == 0 and j == 0:
                        continue
                    if i and j and i != j:
                        continue
                    if cold(lo - i, hi - j):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append((a, b))
print("non-cold positions with no winning move:", missing[:10])
