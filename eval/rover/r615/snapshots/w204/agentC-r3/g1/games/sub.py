"""取石子子游戏：先手必胜/必败判定。

solve(text) 读入首行 "n k"，第二行 k 个互不相同的允许步数（保证含 1）。
必胜输出 "WIN m"（m 为数值最小的必胜首取数），必败输出 "LOSE"（末尾不带换行）。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = []
    while len(steps) < k:
        steps.extend(int(x) for x in lines[idx].split())
        idx += 1
    steps = sorted(steps)

    # win[j] = 当前有 j 颗石子时轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for j in range(1, n + 1):
        for s in steps:
            if s > j:
                break
            if not win[j - s]:
                win[j] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
