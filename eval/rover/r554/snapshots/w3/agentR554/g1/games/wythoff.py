def solve(text: str) -> str:
    a, b = map(int, text.split())
    # Wythoff move: (i,0) or (0,j) or (t,t) with 0 <= i <= a, 0 <= j <= b, 0 <= t <= min(a,b)
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) or (j == 0) or (i == j):
                moves.append((i, j))
    def is_lose(x, y):
        if x > y:
            x, y = y, x
        # Beatty / Weddergoff: losing positions are (floor(n*phi), floor(n*phi^2))
        n = 0
        while True:
            p = (5 ** 0.5 + 1) / 2
            lx = int(n * p)
            ly = int(n * p * p)
            if lx == x and ly == y:
                return True
            if lx > x:
                return False
            n += 1
    for i, j in moves:
        if is_lose(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
