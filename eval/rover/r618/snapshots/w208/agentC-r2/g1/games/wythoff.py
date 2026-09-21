def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) != (j == 0):
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    t = b - a
    if t < 0:
        return False
    return a == int(t * (1 + 5 ** 0.5) / 2)
