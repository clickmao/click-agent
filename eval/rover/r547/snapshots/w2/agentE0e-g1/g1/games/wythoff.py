"""Wythoff 博弈: 字典序最小必胜着法。"""


def _lose(a, b):
    if a > b:
        a, b = b, a
    for n in range(25):
        p = (int(n * (1 + 5 ** 0.5) / 2), int(n * (3 + 5 ** 0.5) / 2))
        if p == (a, b):
            return True
    return False


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    if _lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if _lose(a - i, b - j):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
