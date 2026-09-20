"""Wythoff 博弈：判定先手胜负，并给出字典序最小的必胜着法 (i, j)。

solve(text) 入参为完整 stdin 文本，返回应当写出的 stdout 文本（末尾无换行）。

输入格式：
    一行: a b   (1<=a<=25, 1<=b<=25)
玩法：
    每次可取 (i) 从任意一堆取走任意正数目石子，或
             (ii) 从两堆同时取走相同的正数目石子。取走最后一颗者胜。
输出格式：
    先手必败: 一行 "LOSE"
    否则:     一行 "WIN i j"，i 从第一堆取、j 从第二堆取（可 0，但不同时为 0），
             且 (i, j) 在所有必胜着法中按字典序最小（先比 i 再比 j）。
"""
from typing import List


def _losing(n: int) -> List[bool]:
    """打表：两堆均不超过 n 时的必败态（P-positions, 含 (0,0)）。"""
    rows = [[False] * (n + 1) for _ in range(n + 1)]
    for a in range(n + 1):
        for b in range(n + 1):
            losing = True
            for i in range(1, a + 1):  # 只从第一堆取
                if rows[a - i][b]:
                    losing = False
                    break
            if losing:
                for j in range(1, b + 1):  # 只从第二堆取
                    if rows[a][b - j]:
                        losing = False
                        break
            if losing:
                lim = min(a, b)
                for t in range(1, lim + 1):  # 两堆同取
                    if rows[a - t][b - t]:
                        losing = False
                        break
            rows[a][b] = losing
    return rows


def solve(text: str) -> str:
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])
    rows = _losing(max(a, b))
    for i in range(a + 1):  # 字典序：先比 i 再比 j
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na = a - i
            nb = b - j
            if rows[na][nb]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
