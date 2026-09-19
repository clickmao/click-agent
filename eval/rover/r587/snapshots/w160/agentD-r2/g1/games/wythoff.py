def _cold(a, b):
    # 判断 (a,b) 是否为 Wythoff 博弈的必败点(P-position)
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    # 必败点形如 (floor(d*phi), floor(d*phi)+d)
    phi = (1 + 5 ** 0.5) / 2
    import math
    cx = math.floor(d * phi)
    return x == cx and y == cx + d


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])

    if _cold(a, b):
        return 'LOSE'

    best = None
    # (i, j) 字典序最小: 先比 i 再比 j
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue  # 合法着法: 单堆取 (i,0)/(0,j) 或两堆同取 (i,i)
            if _cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
