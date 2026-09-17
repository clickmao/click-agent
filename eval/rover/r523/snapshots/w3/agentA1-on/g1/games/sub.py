"""取石子子游戏: 先手必胜/必败 + 数值最小的必胜首取数.

stdin: 第一行 n k; 第二行 k 个互不相同的数 s1..sk (含 1).
stdout: `WIN m` 或 `LOSE`.
"""


def _parse(text):
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    # 跳过空行, 稳健取两个非空行
    vals = []
    for ln in lines:
        if ln.strip():
            vals.append(ln.split())
        if len(vals) == 2:
            break
    n, k = int(vals[0][0]), int(vals[0][1])
    steps = [int(x) for x in vals[1][:k]]
    return n, steps


def solve(text):
    n, steps = _parse(text)
    steps = sorted(set(steps))
    # win[i] = 剩余 i 颗时先手是否必胜; 取走最后者胜 => i=0 为必败
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:  # 走一步留给对手必败态
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:  # steps 已升序 => 首个可行即为数值最小
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
