"""Wythoff 博弈: 必败点判定与字典序最小的必胜着法。

读入: 一行两个整数 a b (1<=a<=25, 1<=b<=25)。
玩法: 每次可选 (i) 从任意一堆取走任意正数目的石子, 或
              (ii) 从两堆同时取走相同的正数目的石子;
      取走最后一颗石子者胜。
输出: 先手必败时输出 'LOSE'; 否则输出 'WIN i j' —— 从第一堆取 i 颗、第二堆取 j 颗,
      (i, j) 在全部必胜着法中按字典序最小 (先比 i 再比 j; i, j >= 0 且不同时为 0)。

思路:
  先手必败 <=> 两堆构成 Wythoff 对 (a_k, b_k) = (floor(k*phi), floor(k*phi^2)),
  k >= 0, 含 (0,0)。
  必胜着法: 枚举所有合法 (i, j), 留下使对手处于必败态的着法, 取字典序最小。
  合法 (i,j):
    - i = j = 0 排除;
    - i == j          (两堆同时取等量)
    - i > 0, j == 0   (只动第一堆)
    - i == 0, j > 0   (只动第二堆)
"""


def _losing(a, b):
    """(a, b) 是否为先手必败 (Wythoff 对), 含 (0, 0)。"""
    if a > b:
        a, b = b, a
    k = b - a
    ka = (5 ** 0.5 + 1) / 2
    # a_k = floor(k*phi)
    ak = int(k * ka)
    if ak != a:
        # 浮点误差容错: 在 ak-1, ak, ak+1 中取真值
        for cand in (ak - 1, ak, ak + 1):
            if cand >= 0 and cand == a:
                ak = cand
                break
        else:
            return False
    return True


def solve(text: str) -> str:
    ints = text.split()
    a = int(ints[0])
    b = int(ints[1])

    if _losing(a, b):
        return 'LOSE'

    cands = set()
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == j) or (i > 0 and j == 0) or (i == 0 and j > 0):
                cands.add((i, j))

    for i, j in sorted(cands):
        if _losing(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
