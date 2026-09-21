"""取石子子游戏: 必败/必胜判定。

输入: 第一行 n k; 第二行 k 个互不相同的整数 s1..sk (含 1)。
输出: 先手必胜 => 'WIN m' (m 为数值最小的必胜首取数); 否则 'LOSE'。
"""


def solve(text):
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    n, k = (int(v) for v in lines[0].split())
    steps = [int(v) for v in lines[1].split()]
    steps = sorted(set(steps))

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
