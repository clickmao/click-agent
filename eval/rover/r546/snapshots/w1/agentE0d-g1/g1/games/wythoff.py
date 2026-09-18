def solve(text):
    lines = [ln for ln in text.splitlines() if ln.strip() != '']
    a, b = map(int, lines[0].split()[:2])
    N = max(a, b) + 1

    def losing(x, y):
        cx, cy = x, y
        for d in range(1, min(cx, cy) + 1):
            if dp[cx - d][cy - d]:
                return False
        for d in range(1, cx + 1):
            if dp[cx - d][cy]:
                return False
        for d in range(1, cy + 1):
            if dp[cx][cy - d]:
                return False
        return True

    dp = [[False] * (max(a, b) + 1) for _ in range(max(a, b) + 1)]
    for x in range(max(a, b) + 1):
        for y in range(max(a, b) + 1):
            dp[x][y] = losing(x, y)
    if dp[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if dp[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
