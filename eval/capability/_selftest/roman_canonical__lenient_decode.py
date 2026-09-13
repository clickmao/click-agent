
VALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]

def to_roman(n):
    out = []
    for v, s in VALS:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)

def from_roman(s):
    total = 0
    i = 0
    while i < len(s):
        if i + 1 < len(s) and s[i:i + 2] in {sym for _, sym in VALS}:
            total += dict((sym, v) for v, sym in VALS)[s[i:i + 2]]
            i += 2
        else:
            total += dict((sym, v) for v, sym in VALS)[s[i]]
            i += 1
    return total
