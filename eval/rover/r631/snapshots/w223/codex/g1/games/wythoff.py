from math import isqrt


def floor_phi(d: int) -> int:
    """floor(d * phi) with phi = (1 + sqrt(5)) / 2, exact integer math."""
    return (d + isqrt(5 * d * d)) // 2


def is_cold(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    d = y - x
    return x == floor_phi(d)


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = (int(x) for x in lines[idx].split())

    if is_cold(a, b):
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if is_cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
