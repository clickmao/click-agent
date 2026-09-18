def _nim_win(a):
    r = 0
    for x in a:
        r ^= x
    return r != 0


def solve(text):
    nums = text.split()
    m = int(nums[0])
    a = [int(x) for x in nums[1:1 + m]]
    if not _nim_win(a):
        return "LOSE"
    res = None
    for i in range(m):
        for r in range(1, a[i] + 1):
            b = list(a)
            b[i] -= r
            if not _nim_win(b):
                if res is None or (i + 1, r) < res:
                    res = (i + 1, r)
    return "WIN %d %d" % res
