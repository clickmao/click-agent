def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(x, y):
        for n in range(0, x + 1):
            if (x - n) % 2:
                continue
            k = (x - n) // 2
            if y - n == k:
                return True
        return False

    if losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if losing(a - i, b - j):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
