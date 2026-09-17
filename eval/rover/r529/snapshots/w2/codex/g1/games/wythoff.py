def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    memo = {}

    def win(x, y):
        if (x, y) in memo:
            return memo[(x, y)]
        result = False
        for i in range(1, x + 1):
            if not win(x - i, y):
                result = True
                break
        if not result:
            for j in range(1, y + 1):
                if not win(x, y - j):
                    result = True
                    break
        if not result:
            for t in range(1, min(x, y) + 1):
                if not win(x - t, y - t):
                    result = True
                    break
        memo[(x, y)] = result
        return result

    if not win(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and not win(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
