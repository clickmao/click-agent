"""取石子子游戏：先手必胜/必败判定。"""


def solve(text: str) -> str:
    nums = [int(x) for x in text.split()]
    n, k = nums[0], nums[1]
    moves = sorted(set(nums[2:2 + k]))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
