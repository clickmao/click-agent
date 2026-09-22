def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    # losing positions: (floor(n*phi), floor(n*phi)+n)
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    for n in range(0, 50):
        x = int(n * phi)
        while int((x + 1) * phi) - x < n + 1:
            x += 1
        while x > 0 and int(x * phi) - (x - 1) >= n:
            x -= 1
        y = x + n
        losing.add((x, y))
        losing.add((y, x))
    win_pos = set()
    for i in range(0, 26):
        for j in range(0, 26):
            if (i, j) in losing:
                continue
            ok = False
            for k in range(1, i + 1):
                if (i - k, j) in losing:
                    ok = True
                    break
            if not ok:
                for k in range(1, j + 1):
                    if (i, j - k) in losing:
                        ok = True
                        break
            if not ok:
                for k in range(1, min(i, j) + 1):
                    if (i - k, j - k) in losing:
                        ok = True
                        break
            if ok:
                win_pos.add((i, j))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
