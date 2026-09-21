def _is_losing(x, y):
    """Wythoff 必败点 (冷点): (floor(n*phi), floor(n*phi)+n)。"""
    if x > y:
        x, y = y, x
    # 用整数方式生成冷点, 避免浮点误差: a_n = floor(n*phi)。
    n = 0
    an = 0
    while an < x or an + n < y:
        if an >= x and an + n >= y:
            break
        n += 1
        # floor(n*phi) = floor((n*(1+sqrt(5)))/2)
        num = n * (1 + 5 ** 0.5) / 2.0
        an = int(num)
        if an < x or an + n < y:
            continue
        else:
            break
    for cand in (n, n + 1):
        if cand < 0:
            continue
        an = int(cand * (1 + 5 ** 0.5) / 2.0)
        if an == x and an + cand == y:
            return True
    return x == 0 and y == 0


def solve(text: str) -> str:
    """Wythoff 博弈: 必败输出 'LOSE', 否则输出字典序最小的 'WIN i j'。"""
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])
    if _is_losing(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
