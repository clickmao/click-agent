def solve(text):
    a, b = (int(x) for x in text.split())
    ans = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if i > a or j > b:
                continue
            # after taking i from pile1 and j from pile2
            ra, rb = a - i, b - j
            if ra == rb or min(ra, rb) == 0:
                # must be a winning move: resulting position is losing
                pass
            # losing positions are Wythoff pairs: (floor(n*phi), floor(n*phi^2))
            def losing(x, y):
                if x > y:
                    x, y = y, x
                # (x, y) is a P-position iff x == floor(n*phi) and y == x + n for some n>=0
                n = y - x
                return n >= 0 and x == int(n * 1.618033988749895) and int(n * 1.618033988749895) == x and int(n * 1.618033988749895 + 1e-9) == x
            if losing(ra, rb):
                ans = 'WIN %d %d' % (i, j)
                break
        if ans is not None:
            break
    if ans is None:
        return 'LOSE'
    return ans
