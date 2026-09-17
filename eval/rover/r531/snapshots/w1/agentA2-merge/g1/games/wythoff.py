"""Wythoff 博弈 —— 规范实现 (迭代 DP, 无递归, 覆盖 0..25)。

必败点 (冷点): (0,0) 与 (⌊nφ⌋, ⌊nφ²⌋), n=1,2,...

按 a+b 递增自底向上填表, 保证依赖点 (a-i,b-j) 已就绪。
"""

MAXV = 25

# _LOSE[a][b] = (a,b) 为必败点
_LOSE = [[False] * (MAXV + 1) for _ in range(MAXV + 1)]

for _a, _b in sorted(((a, b) for a in range(MAXV + 1) for b in range(MAXV + 1)),
                     key=lambda p: p[0] + p[1]):
    _has_move_to_lose = False
    for _i in range(_a + 1):
        for _j in range(_b + 1):
            if _i == 0 and _j == 0:
                continue
            # 合法着法: (i) 单堆取 (恰好一堆取 0); (ii) 双堆同取 (i == j)
            if (_i == 0) != (_j == 0) or _i == _j:
                if _LOSE[_a - _i][_b - _j]:
                    _has_move_to_lose = True
                    break
        if _has_move_to_lose:
            break
    _LOSE[_a][_b] = not _has_move_to_lose


def lose(a: int, b: int) -> bool:
    """判定 (a,b) 是否必败点。"""
    return _LOSE[a][b]


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (末尾不带换行)。"""
    a, b = (int(x) for x in text.split()[:2])

    if lose(a, b):
        return "LOSE"

    # 字典序 (i 升序, 再 j 升序) 找第一个到达必败点的着法
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) != (j == 0) or i == j:
                if lose(a - i, b - j):
                    return "WIN %d %d" % (i, j)
    return "LOSE"
