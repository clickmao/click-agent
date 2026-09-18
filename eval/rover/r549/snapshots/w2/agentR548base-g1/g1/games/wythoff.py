def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    if a > b:
        a, b = b, a
    # P-positions: (floor(k*phi), floor(k*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    k = b - a
    pa = int(k * phi)
    pb = pa + k
    if pa == a and pb == b:
        return 'LOSE'
    return 'WIN %d %d' % (pb - b, pa - a)
