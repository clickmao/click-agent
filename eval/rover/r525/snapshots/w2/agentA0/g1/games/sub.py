"""取石子子游戏：判定先手胜负并给出最小必胜首取数。"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    moves = sorted(int(x) for x in lines[idx].split())
    moves = [s for s in moves if 1 <= s <= n] or [s for s in moves]

    # win[i] = 剩余 i 颗时当前行动方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        can = False
        for s in moves:
            if s <= i and not win[i - s]:
                can = True
                break
        win[i] = can

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
