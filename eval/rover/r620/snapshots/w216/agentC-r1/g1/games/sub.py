"""取石子子游戏: 判定先手必胜/必败并给出最小必胜首取数。

solve(text) 读入:
  第一行两个整数 n k
  第二行 k 个互不相同的整数 s1..sk
规则: 每步取走恰好某个允许的数目, 取走最后一颗者胜。
返回: 'WIN m' (m 为数值最小的必胜首取数) 或 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    s = [int(x) for x in lines[2:2 + k]]
    s.sort()

    lo, hi = min(s), max(s)
    win = [False] * (n + 1)
    win[0] = False
    for x in range(1, n + 1):
        for take in s:
            if take > x:
                break
            if not win[x - take]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for take in s:
        if take <= n and not win[n - take]:
            return 'WIN %d' % take
    return 'LOSE'
