"""取石子子游戏: 先手必胜/必败判定及最小必胜首取数。

输入首行: n k (1<=n<=80, 1<=k<=12)
第二行: k 个互不相同的整数 s1..sk (1<=si<=12, 保证含 1)
一步取走恰好某个允许的数目, 取走最后一颗者胜。
输出: 先手必胜则 'WIN m' (m 为数值最小的必胜首取数), 否则 'LOSE'。
"""


def solve(text: str) -> str:
    nums = [int(tok) for tok in text.replace('\n', ' ').replace('\r', ' ').split()]
    n, k = nums[0], nums[1]
    steps = sorted(set(nums[2:2 + k]))

    # win[i] = 剩余 i 颗时当前行动者是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
