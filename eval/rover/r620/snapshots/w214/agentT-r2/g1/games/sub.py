"""取石子游戏：先手胜负判定与最小必胜首取数。

读入: 第一行 n k (石子数, 可选步数个数); 第二行 k 个互不相同的整数 si。
规则: 每次取走恰好某个允许的数目，取走最后一颗者胜。
输出: 'WIN m'（m 为数值最小的必胜首取数）或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    n, k = (int(t) for t in lines[0].split()[:2])
    moves = sorted({int(t) for t in lines[1].split()[:k]})

    # win[x] = 剩余 x 颗时轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
