"""取石子子游戏: 输出 WIN m 或 LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    moves = sorted(int(x) for x in lines[idx].split()) if idx < len(lines) else []
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
