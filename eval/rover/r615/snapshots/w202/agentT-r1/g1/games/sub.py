"""取石子子游戏: 判定先手胜负并给出数值最小的必胜首取数。"""


def solve(text: str) -> str:
    """输入完整 stdin 文本, 返回应写出的 stdout 文本(末尾不带换行)。"""
    lines = text.splitlines()
    if not lines:
        return ""
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]
    steps = sorted(set(steps))[:k] if k else []

    # win[i] = True 表示余下 i 颗时当前行动方必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
