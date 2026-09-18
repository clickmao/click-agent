def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    if not lines:
        return ''
    a, b = map(int, lines[0].split())
    limit = 25
    lose = set()
    for x in range(limit + 1):
        for y in range(limit + 1):
            islose = True
            if x == 0 and y == 0:
                islose = False
            else:
                for i in range(0, x + 1):
                    if not islose:
                        break
                    for j in range(0, y + 1):
                        if i == 0 and j == 0:
                            continue
                        if i > 0 and j > 0 and i != j:
                            continue
                        if (x - i, y - j) in lose:
                            islose = False
                            break
            if islose:
                lose.add((x, y))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
