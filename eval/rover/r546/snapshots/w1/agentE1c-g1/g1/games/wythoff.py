def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    x = (int(5 ** 0.5) + 1) // 2
    while (x + 1) * d <= a + 2:
        x += 1
    while x * d > a:
        x -= 1
    ca = int(x * d)
    cb = int(x * d) + d
    return ca == a and cb == b


def solve(text: str) -> str:
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])
    if _losing(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        j0 = 0
        if not (i == 0):
            pass
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and i == j:
                if na == 0 and nb == 0:
                    cands.append((i, j))
                elif _losing(na, nb):
                    cands.append((i, j))
                continue
            if i == 0:
                if _losing(na, nb):
                    cands.append((i, j))
                continue
            if j == 0:
                if _losing(na, nb):
                    cands.append((i, j))
                continue
    if not cands:
        return 'WIN 0 0'
    i, j = min(cands)
    return 'WIN ' + str(i) + ' ' + str(j)
