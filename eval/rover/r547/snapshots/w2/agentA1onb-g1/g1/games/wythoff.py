"""Wythoff 博弈: 必败点判定 / 字典序最小必胜着法。

输入格式:
    一行两个整数 a b (1<=a<=25, 1<=b<=25)。

玩法: 每次 (i) 从任意一堆取走任意正数; 或 (ii) 从两堆同时取走相同正数。
      取走最后一颗者胜。
输出: 先手必败 -> "LOSE";
      否则 -> "WIN i j" (从第一堆取 i、第二堆取 j), (i,j) 为全部必胜着法中
      按字典序最小者 (先比 i 再比 j; i,j>=0 且不同时为 0)。

依据: Wythoff 必败点 = (floor(k*phi), floor(k*phi^2)), k>=0; 命中即必败。
"""
import math

_PHI = (1.0 + math.sqrt(5.0)) / 2.0
_PHI2 = _PHI * _PHI


def _is_cold(a: int, b: int) -> bool:
    """判断 (a,b) 是否为 Wythoff 必败点 (对称, 输入顺序无关)。"""
    x, y = (a, b) if a <= b else (b, a)
    # 校验 x == floor(k*phi) 对应的 y == floor(k*phi^2)
    if x == 0:
        return y == 0
    k = int(x / _PHI)
    for kk in (k - 1, k, k + 1):
        if kk < 0:
            continue
        if int(math.floor(kk * _PHI)) == x and int(math.floor(kk * _PHI2)) == y:
            return True
    return False


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (不带末尾换行)。"""
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])

    if _is_cold(a, b):
        return "LOSE"

    # 枚举所有合法着法, 取使局面成为必败点者, 按 (i,j) 字典序最小
    best = None
    for i in range(0, a + 1):          # 从第一堆取 i
        for j in range(0, b + 1):      # 从第二堆取 j
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue               # 仅允许: 单堆取 / 双堆等量取
            if _is_cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    # 理论上必存在必胜着法
    return "WIN %d %d" % best
