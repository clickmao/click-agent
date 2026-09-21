"""取石子（subtraction game）：判定先手胜负并给出数值最小的必胜首取数。

约定：solve 返回的字符串末尾不带换行。
"""


def solve(text: str) -> str:
    """text = 完整 stdin 文本；返回 'WIN m' 或 'LOSE'。"""
    lines = text.split("\n")
    n, _k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    # win[x] = 剩 x 颗时当前行动者是否必胜
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
