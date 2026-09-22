"""Wythoff's game: losing position test, lexicographically smallest winning move."""

PHI = (1 + 5 ** 0.5) / 2


def _losing(a, b):
    a, b = (a, b) if a <= b else (b, a)
    for d in range(0, 40):
        if int(d * PHI + 0.5) == a and int(d * PHI * PHI + 0.5) == b:
            return True
    return False


def solve(text):
    nums = text.split()
    a0, b0 = int(nums[0]), int(nums[1])
    if _losing(a0, b0):
        return 'LOSE'
    for i in range(a0 + 1):
        for j in range(b0 + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _losing(a0 - i, b0 - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
