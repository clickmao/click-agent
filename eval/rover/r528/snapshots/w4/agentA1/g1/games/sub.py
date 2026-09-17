"""取石子子游戏 (subtraction game): 判断先手胜负并给出最小必胜首取数。"""


def solve(text: str) -> str:
    data = text.split()
    n, k = int(data[0]), int(data[1])
    moves = [int(x) for x in data[2:2 + k]]

    # win[i] = 先手面对 i 颗石子的玩家是否有必胜策略
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"

    # 数值最小的必胜首取数: 取走 s 后留给对手的位置为必败态
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
