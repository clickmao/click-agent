"""取石子子游戏：必胜/必败判定与最小必胜首取数。"""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])
    # win[i] 为 True 表示还剩 i 颗时轮到走的人可以取胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
