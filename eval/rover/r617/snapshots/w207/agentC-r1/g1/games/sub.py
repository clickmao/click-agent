def solve(text: str) -> str:
    """取石子: 先手必胜输出 'WIN m' (m 为数值最小的必胜首取数), 必败输出 'LOSE'。"""
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    s = [int(x) for x in nums[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(n + 1):
        ok = False
        for t in s:
            if t <= i and not win[i - t]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return "LOSE"
    for t in sorted(set(s)):
        if t <= n and not win[n - t]:
            return "WIN %d" % t
    return "LOSE"
