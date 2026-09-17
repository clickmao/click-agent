"""Ad-hoc probe: brute-force Wythoff cold positions and compare with formula."""
from math import isqrt


def brute(limit):
    cold = set()
    for a in range(limit + 1):
        for b in range(limit + 1):
            win = False
            for i in range(a + 1):
                if not win and (a - i, b) in cold:
                    win = True
            for j in range(1, b + 1):
                if not win and (a, b - j) in cold:
                    win = True
            for t in range(1, min(a, b) + 1):
                if not win and (a - t, b - t) in cold:
                    win = True
            if not win:
                cold.add((a, b))
    return cold


def formula(limit):
    out = set()
    for m in range(0, limit + 2):
        x = (m + isqrt(5 * m * m)) // 2
        out.add((x, x + m))
    return out


B = brute(26)
F = formula(26)
onlyB = sorted(p for p in B if p not in F)
onlyF = sorted(p for p in F if p not in B)
print("brute count", len(B), "formula flagged", len(F))
print("in brute not formula:", onlyB[:20])
print("in formula not brute:", onlyF[:20])
print("sorted brute:", sorted(B)[:20])
