def solve(text):
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    nums = lines[0].split()
    a, b = int(nums[0]), int(nums[1])
    LIM = 30
    lost = set()
    for x in range(0, LIM + 1):
        for y in range(0, LIM + 1):
            if (x == 0 and y == 0):
                lost.add((0, 0))
                continue
            ok = False
            for i in range(0, x + 1):
                for j in range(0, y + 1):
                    if i == 0 and j == 0:
                        continue
                    if (i != 0 and j != 0) and i != j:
                        continue
                    if (x - i, y - j) in lost:
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                lost.add((x, y))
    if (a, b) in lost:
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i != 0 and j != 0) and i != j:
                continue
            if (a - i, b - j) in lost:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
