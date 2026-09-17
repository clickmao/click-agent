def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    def outcome(x, y):
        # True if the player to move with piles (x, y) wins
        if x > y:
            x, y = y, x
        # Cold (P) positions: (floor(n*phi), floor(n*phi^2))
        n = int((y - x) * 0.6180339887498949)
        for cand in (max(n - 2, 0), max(n - 1, 0), n, n + 1, n + 2):
            cx = (cand * 1618033989) // 1000000000
            # use exact comparison with integers to avoid float drift
            pass
        # exact check using integer arithmetic for phi = (1+sqrt(5))/2
        # P-position iff x == floor(n*phi) and y == x + n for n = y - x
        if True:
            d = y - x
            # check x == floor(d * phi)
            # floor(d*phi) where phi = (1+sqrt5)/2 -> (d + isqrt(5*d*d))//2
            from math import isqrt
            px = (d + isqrt(5 * d * d)) // 2
            if x == px and y == x + d:
                return False
        return True

    def is_lose(x, y):
        return not outcome(x, y)

    if is_lose(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            nx, ny = a - i, b - j
            if not is_lose(nx, ny):
                continue
            if best is None or (i, j) < best:
                best = (i, j)
    return "WIN %d %d" % best
