
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
    idx, total = 0, 0
    for v, sym in VALS:
        while s.startswith(sym, idx):
            total += v
            idx += len(sym)
    if idx != len(s):
        return None
    return total if to_roman(total) == s else None   # 互逆判据
