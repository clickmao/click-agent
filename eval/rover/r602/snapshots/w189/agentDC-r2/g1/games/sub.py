"""取石子子游戏（减法博弈）：判定先手胜负并给出字典序/数值最小的必胜首取数。

solve(text) 入参为完整 stdin 文本，返回应当写出的 stdout 文本（末尾无换行）。

输入格式：
    第一行: n k        (1<=n<=80, 1<=k<=12)
    第二行: s1..sk     (互不相同, 1<=si<=12, 保证含 1)
玩法：
    每次取走恰好某个允许的数目，取走最后一颗者胜。
输出格式：
    先手必胜: 一行 "WIN m"，m 为数值最小的必胜首取数
    先手必败: 一行 "LOSE"
"""
from typing import List


def solve(text: str) -> str:
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = sorted(int(x) for x in nums[2:2 + k])
    # win[i] = 剩下 i 颗石子时轮到的玩家是否必胜
    win: List[bool] = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)
    if not win[n]:
        return "LOSE"
    for s in steps:  # steps 已升序，第一个必胜着法即为数值最小者
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
