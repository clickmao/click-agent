"""Wythoff 博弈：判定必败点，否则给出字典序最小的必胜着法。"""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    n = max(a, b)

    losing = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            ok = False
            for d in range(1, i + 1):
                if losing[i - d][j]:
                    ok = True
                    break
            if not ok:
                for d in range(1, j + 1):
                    if losing[i][j - d]:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(i, j) + 1):
                    if losing[i - d][j - d]:
                        ok = True
                        break
            losing[i][j] = not ok

    if losing[a][b]:
        return "LOSE"

    best_i, best_j = None, None
    for i in range(a + 1):
        for j in range(b + 1):
            if (i, j) == (0, 0):
                continue
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if losing[a - i][b - j]:
                best_i, best_j = i, j
                break
        if best_i is not None:
            break

    if best_i is None:
        return "LOSE"
    return "WIN %d %d" % (best_i, best_j)
