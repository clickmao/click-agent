LIM = 60

def _lose_pairs():
    pairs = []
    seen = set()
    a = 0
    while True:
        while a in seen:
            a += 1
        b = a + len(pairs) + 1
        if b > LIM:
            break
        pairs.append((a, b))
        seen.add(a)
        seen.add(b)
        a += 1
    return set(pairs)

_LOSE = _lose_pairs()

def _is_lose(a, b):
    x, y = (a, b) if a <= b else (b, a)
    return (x, y) in _LOSE

def solve(text):
    toks = text.split()
    if not toks:
        return ''
    a = int(toks[0])
    b = int(toks[1])
    if _is_lose(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        if i > 0 and _is_lose(a - i, b):
            cands.append((i, 0))
    for j in range(0, b + 1):
        if j > 0 and _is_lose(a, b - j):
            cands.append((0, j))
    for d in range(1, min(a, b) + 1):
        if _is_lose(a - d, b - d):
            cands.append((d, d))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
