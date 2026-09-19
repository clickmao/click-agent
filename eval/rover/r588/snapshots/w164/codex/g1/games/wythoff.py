def is_cold(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    # a = floor(k*phi), b = a + k for the unique integer k
    k = b - a
    if a == int(k * (5 ** 0.5 + 1) / 2) and b == a + k:
        return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if is_cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
