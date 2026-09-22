"""取石子子游戏：先手必胜/必败判定。

输入格式:
    第一行 n k
    第二行 k 个互不相同的整数 s1..sk (含 1)
输出格式:
    WIN m  —— m 为数值最小的必胜首取数
    LOSE
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    n, k = (int(x) for x in lines[idx].split()[:2])
    idx += 1
    moves = []
    while idx < len(lines) and len(moves) < k:
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in moves:
            if s > stones:
                break
            if not win[stones - s]:
                win[stones] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
