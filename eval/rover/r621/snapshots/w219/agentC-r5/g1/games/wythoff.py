"""Wythoff 博弈: 判定必败点, 否则给出字典序最小的必胜着法。

入参为完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行)。
"""


def _losing(limit):
    lose = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
            ok = False
            for i in range(a + 1):
                j = b
                if i == 0 and j == 0:
                    continue
                if i > 0 and i != j:
                    continue
                if lose[a - i][b - j]:
                    ok = True
                    break
            if not ok:
                for j in range(b + 1):
                    if j == 0:
                        continue
                    if lose[a][b - j]:
                        ok = True
                        break
            lose[a][b] = not ok
    return lose


_LOSE = _losing(25)


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _LOSE[a][b]:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _LOSE[a - i][b - j]:
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
