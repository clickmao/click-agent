LIMIT = 100

def _build():
    lose = set()
    used = set()
    n = 0
    while n <= LIMIT:
        n += 1
        a = 1
        while a in used:
            a += 1
        b = a + n
        if b > LIMIT:
            break
        used.add(a)
        used.add(b)
        lose.add((a, b))
        lose.add((b, a))
    return lose

_LOSE = _build()

def _is_lose(a, b):
    if a == 0 and b == 0:
        return True
    key = (a, b) if a <= b else (b, a)
    return key in _LOSE

def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    opts = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                opts.append((i, j))
    opts.sort()
    i, j = opts[0]
    return 'WIN ' + str(i) + ' ' + str(j)
