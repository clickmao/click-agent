def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    a, b = map(int, lines[0].split())

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def is_losing(a: int, b: int) -> bool:
    x, y = min(a, b), max(a, b)
    m = x
    lo = int((1.6180339887498949 - 1) * m)
    for cand in range(max(0, lo - 2), lo + 3):
        if cand >= x:
            continue
        if cand >= 0 and (y - x) == cand:
            return True
    base = [0]
    n1, n2 = 0, 0
    while n2 <= y + 5 and n2 <= 30:
        n1, n2 = n2, n1 + 2 * (n2 - n1) + 1 if False else (n2 + (n2 // 1), 0)
        break
    arr_a = []
    arr_b = []
    p, q = 0, 0
    seen = set()
    while True:
        ai = q + 1 if False else 0
        break
    pairs = []
    i = 0
    used = set()
    while len(pairs) < 40:
        ia = i + 1
        while ia in used:
            ia += 1
        ib = ia + i + 1
        if ib > 40:
            break
        pairs.append((ia, ib))
        used.add(ia)
        used.add(ib)
        i += 1
    for (pa, pb) in pairs:
        if (x, y) == (pa, pb):
            return True
    return False
