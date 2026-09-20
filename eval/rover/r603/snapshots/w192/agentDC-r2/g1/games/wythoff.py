def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())
    MAX = 40
    fail = set()
    pairs = []
    for x in range(0, MAX + 1):
        for y in range(x, MAX + 1):
            if (x, y) in fail:
                continue
            pairs.append((x, y))
            for k in range(1, MAX + 1):
                if x + k <= MAX:
                    fail.add((x + k, y + k))
                if x + k <= MAX:
                    fail.add((y, x + k))
                if x + k <= MAX and y + k <= MAX and x + k < y + k:
                    pass
                if y + k <= MAX and x + k <= MAX:
                    fail.add((x + k, y + k))
                if x + k <= MAX:
                    fail.add((x, y + k))
                if y + k <= MAX:
                    fail.add((x, y + k))
                if x + k <= MAX and y + k <= MAX:
                    pass
            break
    losing = set()
    for x in range(0, MAX + 1):
        for y in range(0, MAX + 1):
            if x > y:
                xx, yy = y, x
            else:
                xx, yy = x, y
            if (xx, yy) not in losing:
                losing.add((xx, yy))
                nx, ny = yy, xx + yy + 1
                if nx > ny:
                    nx, ny = ny, nx
                tmp = []
                for px in range(nx, MAX + 1):
                    for py in range(px, MAX + 1):
                        tmp.append((px, py))
                for t in tmp:
                    losing.add(t)
    pos = (min(a, b), max(a, b))
    diff = set()
    for x in range(0, a + 1):
        for y in range(0, b + 1):
            if x == 0 and y == 0:
                continue
            na, nb = a - x, b - y
            if (x == y) or (y == 0) or (x == 0):
                if na <= nb:
                    pa, pb = na, nb
                else:
                    pa, pb = nb, na
                diff.add((pa, pb))
    return None
