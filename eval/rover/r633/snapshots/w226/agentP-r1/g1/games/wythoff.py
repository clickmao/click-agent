def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    LIM = 26
    LOSE = set()
    for x in range(0, LIM):
        for y in range(0, LIM):
            ok = False
            for i in range(0, x + 1):
                for j in range(0, y + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0 and i != j:
                        continue
                    if (x - i, y - j) in LOSE:
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                LOSE.add((x, y))
    if (a, b) in LOSE:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in LOSE:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
