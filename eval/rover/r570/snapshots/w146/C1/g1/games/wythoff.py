_PHI = (1 + 5 ** 0.5) / 2


def _cold_positions(limit):
    """Wythoff cold positions (A_i, A_i + i), A_i = floor(i*phi), coords <= limit."""
    cold = set()
    i = 0
    while True:
        x = int(i * _PHI)
        y = x + i
        if x > limit and y > limit:
            break
        cold.add((x, y))
        i += 1
    return cold


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    cold = _cold_positions(max(a, b))

    def is_losing(x, y):
        return (x, y) in cold or (y, x) in cold

    if is_losing(a, b):
        return 'LOSE'
    for di in range(0, a + 1):
        for dj in range(0, b + 1):
            if di == 0 and dj == 0:
                continue
            if is_losing(a - di, b - dj):
                return 'WIN %d %d' % (di, dj)
    return 'LOSE'
