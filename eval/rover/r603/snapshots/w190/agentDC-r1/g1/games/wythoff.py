def _lose_pairs(limit):
    pairs = set()
    for a in range(limit + 1):
        for b in range(limit + 1):
            x, y = min(a, b), max(a, b)
            if (x, y) in pairs:
                continue
            # check if losing: no move to a smaller losing position
            losing = True
            for i in range(x + 1):
                for j in range(y + 1):
                    if i == 0 and j == 0:
                        continue
                    if i <= x and j <= y and (i != 0 or j != 0):
                        pass
            # brute force via game DP below instead
    return pairs


def solve(text):
    a, b = map(int, text.split())
    X, Y = max(a, b), min(a, b)
    # DP over positions (x, y) with x >= y, x <= X
    N = max(a, b)
    win = {}
    for x in range(0, N + 1):
        for y in range(0, x + 1):
            if x == 0 and y == 0:
                win[(x, y)] = False
                continue
            w = False
            # take from pile x (larger) some t>0
            for t in range(1, x + 1):
                nx, ny = x - t, y
                if nx < ny:
                    nx, ny = ny, nx
                if not win[(nx, ny)]:
                    w = True
                    break
            if not w:
                for t in range(1, y + 1):
                    nx, ny = x - t, y - t
                    if nx < ny:
                        nx, ny = ny, nx
                    if not win[(nx, ny)]:
                        w = True
                        break
            win[(x, y)] = w
    if not win[(X, Y)]:
        return 'LOSE'
    # find lexicographically smallest (i, j) in terms of pile-1 take i, pile-2 take j
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # move must be valid: either take from one pile only, or equal from both
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            u, v = max(na, nb), min(na, nb)
            if not win[(u, v)]:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN {} {}'.format(best[0], best[1])
