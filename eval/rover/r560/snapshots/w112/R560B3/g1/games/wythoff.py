def solve(text):
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    # Cold (P) positions: (floor(n*phi), floor(n*phi^2))
    is_p = False
    n = 0
    while True:
        x = (n * 267914296) // 433494437  # floor(n * (sqrt(5)-1)/2) approximation is unreliable
        n += 1
        if x > 25:
            break
    # exact check for small bounds
    cold = []
    m = 0
    while True:
        aa = (m * 1618033989) // 1000000000
        if aa > 25:
            break
        bb = aa + m
        cold.append((aa, bb))
        m += 1
    # recompute exactly (avoid float drift)
    cold = []
    m = 0
    while True:
        aa = None
        lo, hi = 0, 100
        while lo <= hi:
            mid = (lo + hi) // 2
            if mid * mid <= 5 * m * m:
                aa = mid
                lo = mid + 1
            else:
                hi = mid - 1
        aa = (m + aa) // 2
        if aa > 25:
            break
        cold.append((aa, aa + m))
        m += 1
    if (a, b) in cold:
        return 'LOSE'
    # find lexicographically smallest winning move (i, j) with i from pile1, j from pile2
    # try i from 0..a, j from 0..b, in lexicographic order
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if not (i == 0 or j == 0 or i == j):
                continue
            if na > nb:
                key = (nb, na)
            else:
                key = (na, nb)
            if key in cold:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
