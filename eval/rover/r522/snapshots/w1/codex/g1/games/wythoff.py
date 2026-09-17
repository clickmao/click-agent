def _cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    return a == (d * (1 + 5 ** 0.5) // 2)


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])

    if _cold(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            with_i = 0 <= i <= a
            with_j = 0 <= j <= b
            if not (with_i and with_j):
                continue
            # moves: (i,0) or (0,j) or (t,t) with t=i=j
            valid = (j == 0) or (i == 0) or (i == j)
            if not valid:
                continue
            if _cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN %d %d" % best
