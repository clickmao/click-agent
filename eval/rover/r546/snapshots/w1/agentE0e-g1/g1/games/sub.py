"""取石子子游戏：先手胜负与最小必胜首取数。"""


def solve(text: str) -> str:
    """返回 WIN m 或 LOSE。"""
    tokens = text.split()
    n, k = int(tokens[0]), int(tokens[1])
    moves = sorted(int(t) for t in tokens[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if i - s >= 0 and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if n - s >= 0 and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
