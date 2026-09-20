def _is_beaten(x: int, y: int) -> bool:
    lo = x if x < y else y
    hi = y if x < y else x
    d = hi - lo
    return lo == (d * (1 + 5 ** 0.5) / 2 // 1)


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_beaten(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
