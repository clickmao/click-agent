def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    limit = max(a, b) + 1
    cold = set()
    x = 0
    while True:
        for y in range(0, x + 1):
            if (x, y) in cold:
                continue
            ok = True
            # 从第一堆取 i 颗：需要 (x-i, y) 不在 cold
            for i in range(1, x + 1):
                if (x - i, y) in cold:
                    ok = False
                    break
            if ok:
                # 从第二堆取 j 颗
                for j in range(1, y + 1):
                    if (x, y - j) in cold:
                        ok = False
                        break
            if ok:
                # 两堆同时取相同数目
                for t in range(1, min(x, y) + 1):
                    if (x - t, y - t) in cold:
                        ok = False
                        break
            if ok:
                cold.add((x, y))
                cold.add((y, x))
        x += 1
        if x > limit:
            break

    if (a, b) in cold:
        return 'LOSE'

    best = None
    # 从第一堆取 i 颗，第二堆取 0 颗（含 i=0 即不动第一堆）
    for i in range(0, a + 1):
        rem_a = a - i
        if (rem_a, b) in cold:
            best = (i, 0)
            break
    if best is None:
        # 从第二堆取 j 颗
        for j in range(0, b + 1):
            rem_b = b - j
            if (a, rem_b) in cold:
                best = (0, j)
                break
    if best is None:
        # 两堆同时取相同数目
        for t in range(1, min(a, b) + 1):
            if (a - t, b - t) in cold:
                best = (t, t)
                break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
