"""取石子子游戏: 先手必胜/必败判定。

输入格式:
    第一行: n k   (1<=n<=80, 1<=k<=12)
    第二行: k 个互不相同的整数 s1..sk (1<=si<=12, 且保证含 1)

玩法: 两人轮流取, 每次取走恰好某个允许数目, 取走最后一颗者胜。
输出: 先手必胜 -> "WIN m" (m 为数值最小的必胜首取数); 否则 -> "LOSE"。
"""


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (不带末尾换行)。"""
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = sorted(int(x) for x in nums[2:2 + k])

    # win[i] = 剩 i 颗时轮到行动方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    # 数值最小的必胜首取数
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"  # 理论不可达 (win[n] 为真必有出边)
