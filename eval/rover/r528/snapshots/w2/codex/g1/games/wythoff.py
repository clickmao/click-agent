def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    memo = {}

    def losing(x, y):
        key = (x, y)
        if key in memo:
            return memo[key]
        memo[key] = False
        res = True
        for i in range(1, x + 1):
            if losing(x - i, y):
                res = False
                break
        if res:
            for j in range(1, y + 1):
                if losing(x, y - j):
                    res = False
                    break
        if res:
            for t in range(1, min(x, y) + 1):
                if losing(x - t, y - t):
                    res = False
                    break
        memo[key] = res
        return res

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
