"""Wythoff's game: WIN i j / LOSE.

stdin format:
    a b
"""


def _lose(n):
    # set of losing pairs (x, y) with x <= y and max(x, y) <= n
    pairs = set()
    for x in range(0, n + 1):
        for y in range(x, n + 1):
            if (x, y) in pairs:
                continue
            # find if any move reaches an already-losing pair
            losing = True
            # from one pile
            for yy in range(0, y):
                if (min(x, yy), max(x, yy)) in pairs:
                    losing = False
                    break
            if losing:
                for xx in range(0, x):
                    if (min(xx, y), max(xx, y)) in pairs:
                        losing = False
                        break
            if losing:
                # both piles same amount
                for d in range(1, x + 1):
                    if (min(x - d, y - d), max(x - d, y - d)) in pairs:
                        losing = False
                        break
            if losing:
                pairs.add((x, y))
    return pairs


def solve(text: str) -> str:
    nums = text.split()
    if not nums:
        return ''
    a = int(nums[0])
    b = int(nums[1])
    maxn = max(a, b) + 1
    pairs = _lose(maxn)

    key = (min(a, b), max(a, b))
    if key in pairs:
        return 'LOSE'

    best = None
    # from one pile only
    for i in range(1, a + 1):
        k2 = (min(a - i, b), max(a - i, b))
        if k2 in pairs:
            best = (i, 0)
            break
    if best is None:
        for j in range(1, b + 1):
            k2 = (min(a, b - j), max(a, b - j))
            if k2 in pairs:
                best = (0, j)
                break
    if best is None:
        for d in range(1, min(a, b) + 1):
            k2 = (a - d, b - d)
            if k2[0] > k2[1]:
                k2 = (k2[1], k2[0])
            if k2 in pairs:
                best = (d, d)
                break
    return 'WIN %d %d' % best
