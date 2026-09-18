"""Wythoff 博弈: 必败点判定与字典序最小必胜着法。"""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(x, y):
        return x == y == 0

    # 预计算必败点集合 (Beatty 序列)
    lose = set()
    phi = (1 + 5 ** 0.5) / 2
    for n in range(0, 30):
        p = int(n * phi)
        q = p + n
        lose.add((p, q))
        lose.add((q, p))
    lose.add((0, 0))

    if (a, b) in lose:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            di = i
            dj = j
            ok = False
            # 从第一堆取 i 颗
            if j == 0 and di <= a:
                if (a - di, b) in lose:
                    ok = True
            # 从第二堆取 j 颗
            if i == 0 and dj <= b:
                if (a, b - dj) in lose:
                    ok = True
            # 两堆同取
            if i == j and dj <= b and di <= a:
                if (a - di, b - dj) in lose:
                    ok = True
            if ok:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
