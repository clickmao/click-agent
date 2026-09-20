def _lose(a, b):
    if a > b:
        a, b = b, a
    pairs = set()
    k = 0
    while True:
        x = int(k * (1 + 5 ** 0.5) / 2)
        while x * x - x * k - k * k < 0:
            x += 1
        while x - 1 > 0 and (x - 1) * (x - 1) - (x - 1) * k - k * k >= 0:
            x -= 1
        if x > 25 and x + k > 25:
            break
        pairs.add((x, x + k))
        k += 1
    return (a, b) in pairs


def solve(text):
    a, b = map(int, text.split()[:2])
    if _lose(a, b):
        return 'LOSE'
    cand = [(0, b), (a, 0), (a, b)]
    d = min(a, b)
    if d > 0:
        cand.append((d, d))
    cand = sorted(set(cand))
    for (i, j) in cand:
        if i == 0 and j == 0:
            continue
        if _lose(a - i, b - j):
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
