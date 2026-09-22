"""Wythoff 博弈: 必败点判定, 必胜时给出字典序最小的 (i, j)。"""

_MAXV = 40


def _win(a, b):
    # 动态规划: win[a][b] = 轮到行动方是否必胜
    w = [[False] * (_MAXV + 1) for _ in range(_MAXV + 1)]
    for a in range(_MAXV + 1):
        for b in range(_MAXV + 1):
            if a == 0 and b == 0:
                w[a][b] = False
                continue
            res = False
            for i in range(1, a + 1):
                if not w[a - i][b]:
                    res = True
                    break
            if not res:
                for j in range(1, b + 1):
                    if not w[a][b - j]:
                        res = True
                        break
            if not res:
                for d in range(1, min(a, b) + 1):
                    if not w[a - d][b - d]:
                        res = True
                        break
            w[a][b] = res
    return w


_W = _win(_MAXV, _MAXV)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if not _W[a][b]:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取任意正数, 或两堆同时取相同的正数
            if i > 0 and j > 0 and i != j:
                continue
            if not _W[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
