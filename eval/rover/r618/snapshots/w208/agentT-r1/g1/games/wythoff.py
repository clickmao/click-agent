def _bad_points(limit):
    bad = set()
    m = 0
    while True:
        x = (m * (1 + 5 ** 0.5) / 2.0) + 1e-9
        x = int(x)
        y = x + m
        if x > limit or y > limit:
            break
        bad.add((x, y))
        bad.add((y, x))
        m += 1
    return bad


def solve(text: str) -> str:
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])
    bad = _bad_points(25)
    if (a, b) in bad:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if (a - i, b - j) in bad:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
