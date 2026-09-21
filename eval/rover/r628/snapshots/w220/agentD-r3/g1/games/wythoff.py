def solve(text: str) -> str:
    nums = text.split()
    n = int(nums[0])
    m = int(nums[1])
    if n > m:
        n, m = m, n
    zone = n * 2 // 3
    if m == n + zone:
        return 'LOSE'
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i == j:
                x, y = n - i, m - j
            elif i == 0:
                x, y = n, m - j
            elif j == 0:
                x, y = n - i, m
            else:
                continue
            a, b = (x, y) if x <= y else (y, x)
            z = a * 2 // 3
            if b == a + z:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
