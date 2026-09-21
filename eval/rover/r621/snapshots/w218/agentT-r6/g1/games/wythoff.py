"""Wythoff 博弈: 必败点判定与字典序最小的必胜着法。

输入: 一行两个整数 a b (1<=a<=25, 1<=b<=25)
可选: (i) 从任意一堆取走任意正数, (ii) 从两堆取走相同正数。
输出: 先手必败则 'LOSE', 否则 'WIN i j' —— i,j>=0 且不同时为 0,
      在所有必胜着法中按 (i, j) 字典序最小。
"""


def _losing(MAX):
    """返回最大堆值 <= MAX 范围内所有必败点 (n, m) 的集合。"""
    losing = set()
    for s in range(0, MAX + 1):
        for n in range(s, MAX + 1):
            m = n + s
            if m > MAX:
                break
            ok = True
            for i in range(1, n + 1):
                if (n - i, m) in losing or (m, n - i) in losing:
                    ok = False
                    break
            if ok:
                for j in range(1, m + 1):
                    if (n, m - j) in losing or (m - j, n) in losing:
                        ok = False
                        break
            if ok:
                for t in range(1, n + 1):
                    if (n - t, m - t) in losing:
                        ok = False
                        break
            if ok:
                losing.add((n, m))
                losing.add((m, n))
                break
    return losing


def solve(text: str) -> str:
    nums = [int(tok) for tok in text.split()]
    a, b = nums[0], nums[1]

    losing = _losing(max(a, b))

    if (a, b) in losing:
        return 'LOSE'

    best = None
    # (i, j) 字典序最小: 先按 i 升序, 再按 j 升序
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            valid = False
            if j == 0:
                valid = i > 0            # 只从第一堆取
            elif i == 0:
                valid = j > 0            # 只从第二堆取
            elif i == j:
                valid = True             # 两堆取相同
            if not valid:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
