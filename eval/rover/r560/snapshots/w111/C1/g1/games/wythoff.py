def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        for n in range(0, max(x, y) + 2):
            p = (n * (1 + 5 ** 0.5)) // 2
            q = p + n
            if p > x:
                break
            if p == x and q == y:
                return True
        return False

    if losing(a, b):
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
