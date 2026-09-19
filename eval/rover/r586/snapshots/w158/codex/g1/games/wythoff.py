def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    limit = max(a, b)

    losing = {(0, 0)}
    positions = sorted(
        ((x, y) for x in range(limit + 1) for y in range(limit + 1)),
        key=lambda p: (max(p), p[0] + p[1]),
    )
    for x, y in positions:
        if (x, y) in losing:
            continue
        movable = False
        for px, py in losing:
            if px == x or py == y or (px < x and x - y == px - py):
                movable = True
                break
        if not movable:
            losing.add((x, y))

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
