def _cold(limit):
    cold = {(0, 0)}
    k = 1
    while True:
        a = int(k * ((5 ** 0.5 + 1) / 2))
        b = a + k
        if a > limit and b > limit:
            break
        cold.add((a, b))
        cold.add((b, a))
        k += 1
    return cold


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    cold = _cold(max(a, b))
    if (a, b) in cold:
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or i == j):
                continue
            if (a - i, b - j) in cold:
                return "WIN %d %d" % (i, j)
    return "LOSE"
