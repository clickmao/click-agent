"""取石子子游戏 (subtraction game) 必胜/必败判定。

solve(text) -> str
  入参 text = 完整 stdin 文本:
    第一行: n k
    第二行: k 个互不相同的允许步数 s1..sk (含 1)
  返回: 先手必胜 -> "WIN m" (m 为数值最小的必胜首取数); 否则 "LOSE"。
"""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    steps = [int(x) for x in data[2:2 + k]]

    # win[x] : 剩余 x 颗时轮到行动者是否必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in steps:
            if s <= x and not win[x - s]:
                w = True
                break
        win[x] = w

    if not win[n]:
        return 'LOSE'

    # 数值最小的必胜首取数 m: 取走 m 后对手局面必败
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
