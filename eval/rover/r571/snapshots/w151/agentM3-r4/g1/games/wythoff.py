def is_losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    i = int((x * (5 ** 0.5 + 1)) / 2)
    while (i * (5 ** 0.5 + 1)) // 2 < x:
        i += 1
    while i > 0 and (i * (5 ** 0.5 + 1)) // 2 > x:
        i -= 1
    return x == (i * (5 ** 0.5 + 1)) // 2 and y == x + i


def solve(text):
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
