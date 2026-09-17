"""取石子子游戏: 判断先手胜负, 必胜时给数值最小的必胜首取数。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))

    # win[i] = 当前有 i 颗石子时, 轮到行动者是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m > i:
                break
            if not win[i - m]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
