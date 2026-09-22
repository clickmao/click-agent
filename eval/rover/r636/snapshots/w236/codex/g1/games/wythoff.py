import math

PHI = (1.0 + math.sqrt(5.0)) / 2.0


def _is_cold(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    t = int(d * PHI)
    if (t + 1) <= d / PHI:
        t += 1
    elif t > d / PHI:
        t -= 1
    return x == t


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    if _is_cold(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
