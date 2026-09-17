"""取石子子游戏: 判定先手必胜/必败, 必胜时给出数值最小的首取数。

输入: 首行 n k; 次行 k 个互不相同的可取石子数 (含 1)。
取走最后一颗者胜。
输出: 必胜 -> "WIN m" (m 为最小的必胜首取数); 必败 -> "LOSE"。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    moves = [int(x) for x in lines[idx].split()][:k]

    # win[i] = 剩 i 颗时当前行动者是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    # 理论不可达
    return "LOSE"
