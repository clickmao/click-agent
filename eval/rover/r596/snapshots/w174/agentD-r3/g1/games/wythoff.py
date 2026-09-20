def _cold(limit):
    cold = set()
    b_used = set()
    a = 0
    while a <= limit:
        if a in b_used:
            a += 1
            continue
        b = min(x for x in range(limit + 1) if x not in b_used and x > a)
        cold.add((a, b))
        cold.add((b, a))
        b_used.add(a)
        b_used.add(b)
        a += 1
    return cold


def solve(text):
    parts = text.split()
    init_a = int(parts[0])
    init_b = int(parts[1])
    limit = max(init_a, init_b)
    cold = _cold(limit)
    for i in range(init_a + 1):
        for j in range(init_b + 1):
            if i == 0 and j == 0:
                continue
            if (i == j or i == 0 or j == 0) and (init_a - i, init_b - j) in cold:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
