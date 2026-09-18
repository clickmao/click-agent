"""取石子子游戏：必败/必胜判定与最小必胜首取数。

stdin 首行: n k
第二行: k 个互不相同的可取石子数 s1..sk（含 1）。
输出 'WIN m'（m 为数值最小的必胜首取数）或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    # win[x] = 剩 x 颗、轮到当前行动者时是否必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
