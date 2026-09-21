"""取石子子游戏：判定先手胜负并给出数值最小的必胜首取数。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]
    moves = sorted(set(s for s in steps if s <= n))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if not win[n - s]:
            return "WIN %d" % s
