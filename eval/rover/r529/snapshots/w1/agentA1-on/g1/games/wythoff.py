"""Wythoff 博弈必胜手 (字典序最小)。

规格:
  一行: a b  (1<=a,b<=25)
玩法: 每次可选 (i) 从任意一堆取走任意正数目, 或 (ii) 从两堆同时取走相同的
      正数目; 取走最后一颗者胜。
输出: 先手必败 -> "LOSE"; 否则 "WIN i j" —— 从第一堆取 i 颗、第二堆取 j 颗,
      在全部必胜着法中按字典序最小 (先比 i 再比 j; i,j>=0 且不同时为 0)。

判定: 必败点 (冷点) 恰为 (floor(n*phi), floor(n*phi^2)), n>=0, phi=(1+sqrt5)/2。
      以 (a,b) 为堆数的着法枚举: 单堆取 / 双堆同时取; 目标须为必败点。
"""
import math

_PHI = (1.0 + math.sqrt(5.0)) / 2.0


def _is_cold(x: int, y: int) -> bool:
    """判断 (x,y) 是否为 Wythoff 必败点 (冷点); 无序对。"""
    lo, hi = (x, y) if x <= y else (y, x)
    n = int((lo + 0.0) / _PHI // 1) if False else int(hi - lo)  # 占位, 下面覆盖
    # 直接用公式反推: 冷点 hi-lo = n, lo = floor(n*phi), hi = floor(n*phi^2)
    n = int(round((hi - lo) / _PHI)) if False else None
    # 稳定做法: 由差值 d = hi-lo 唯一确定 n
    d = hi - lo
    n0 = int((d + 0.5) / _PHI) if False else None
    # 直接枚举小范围 (n<=25 足够) 更稳妥, 但用公式需注意浮点误差:
    # 用整数判据: a=floor(n*phi) 当且仅当 floor(a/phi^2) == n - a ... 采用
    # 精确性质: (x,y) 冷点 <=> floor((y-x)*phi) == x 且 y-x 为整数。
    return math.floor(d * _PHI) == lo


def solve(text: str) -> str:
    """纯函数: stdin 文本 -> stdout 文本 (不带末尾换行)。"""
    a, b = (int(x) for x in text.split()[0:2])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    # 徒: 从第一堆取 i, 从第二堆取 j; (i,j) != (0,0); i<=a, j<=b
    # 着法须使对手面对冷点: (a-i, b-j) 为冷点
    # 枚举 i 升序, 对每个 i 枚举 j 升序以保证字典序最小
    cand = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取 or 双堆同取
            if (i == 0) or (j == 0) or (i == j):
                if _is_cold(a - i, b - j):
                    cand.append((i, j))
    cand.sort()
    i, j = cand[0]
    return 'WIN %d %d' % (i, j)
