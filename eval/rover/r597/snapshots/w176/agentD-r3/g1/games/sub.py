"""取石子子游戏：先手胜负与最小必胜首取。"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        if lines[idx].strip():
            moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in moves:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
