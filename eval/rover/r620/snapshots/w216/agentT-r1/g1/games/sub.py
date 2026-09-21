"""取石子子游戏: 先手必败/必胜判定。

输入格式:
    第一行两个整数 n k (1<=n<=80 为石子数, 1<=k<=12 为可选步数个数)
    第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 且保证其中含 1)

玩法: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。

输出:
    先手必胜 => 一行 `WIN m` (m 为数值最小的必胜首取数)
    先手必败 => 一行 `LOSE`
"""


def solve(text: str) -> str:
    """入参=完整 stdin 文本, 返回=应当写出的 stdout 文本(末尾不带换行)。"""
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())[:k]

    # win[i] = 剩 i 颗石子且轮到当前行动者时, 当前行动者是否必胜。
    # 终止: win[0] = False (无子可取者输)。
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s > i:
                break  # steps 已升序
            if not win[i - s]:
                w = True
                break
        win[i] = w

    if not win[n]:
        return "LOSE"
    # steps 升序 => 第一个使对手处于必败态的就是数值最小的必胜首取数
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
