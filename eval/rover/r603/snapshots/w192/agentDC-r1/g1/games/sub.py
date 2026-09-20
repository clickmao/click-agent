"""取石子子游戏: 输出 WIN m (最小必胜首取) 或 LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return 'LOSE'
    head = lines[idx].split()
    n, k = int(head[0]), int(head[1])
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        for tok in lines[idx].split():
            if len(moves) < k:
                moves.append(int(tok))
        idx += 1
    moves = sorted(set(moves))

    alive = [False] * (n + 1)
    alive[0] = False
    for total in range(1, n + 1):
        win = False
        for s in moves:
            if s <= total and not alive[total - s]:
                win = True
                break
        alive[total] = win

    if not alive[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not alive[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
