import games.wythoff as w

for a in range(1, 26):
    for b in range(1, 26):
        if w._is_cold(a, b):
            continue
        lo, hi = (a, b) if a <= b else (b, a)
        found = None
        for i in range(lo + 1):
            for j in range(hi + 1):
                if i == 0 and j == 0:
                    continue
                if i != 0 and j != 0 and i != j:
                    continue
                if w._is_cold(lo - i, hi - j):
                    found = (i, j)
                    break
            if found:
                break
        if not found:
            print("NO WINNING MOVE", a, b, "cold=", sorted(w._COLD))
            raise SystemExit(1)
print("every non-cold position has a found winning move")
