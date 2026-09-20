"""取石子子游戏: 判定先手胜负最优首取。

solve(text) 读入: 第一行 n k; 第二行 k 个互不相同的可取数(含 1)。
输出 'WIN m' (m 为数值最小的必胜首取数) 或 'LOSE', 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
