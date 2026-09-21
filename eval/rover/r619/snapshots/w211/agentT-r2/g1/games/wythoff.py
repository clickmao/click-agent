"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


LIMIT = 25


def solve(text: str) -> str:
    nums = [int(x) for x in text.split()]
    a, b = nums[0], nums[1]

    losing = set()
    used = set()
    n = 0
    while True:
        x = (n * (1 + 5 ** 0.5) / 2) // 1
        x = int(x)
        while x in used or (x + n) in used or x < 0:
            x += 1
        y = x + n
        if x > LIMIT and y > LIMIT:
            break
        losing.add((x, y))
        losing.add((y, x))
        used.add(x)
        used.add(y)
        n += 1

    if (a, b) in losing:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            legal = (i == 0 and j > 0) or (j == 0 and i > 0) or (i == j)
            if not legal:
                continue
            if (a - i, b - j) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
