"""取石子子游戏: 必败/必胜判定与最小必胜首取。

读入: 第一行两个整数 n k (1<=n<=80 石子数, 1<=k<=12 步数种数);
      第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 必含 1)。
玩法: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。
输出: 先手必胜时输出 'WIN m' (m = 数值最小的必胜首取数); 否则输出 'LOSE'。
"""


def solve(text: str) -> str:
    ints = text.split()
    n = int(ints[0])
    k = int(ints[1])
    steps = sorted(int(x) for x in ints[2:2 + k])

    # win[i] = 剩 i 颗、轮到手者是否有必胜策略。剩 0 颗者无法行动 => 输。
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:  # steps 已升序 => 第一个可行即为数值最小的必胜首取
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
