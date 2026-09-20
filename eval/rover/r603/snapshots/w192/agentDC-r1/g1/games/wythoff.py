"""Wythoff 博弈: 输出 WIN i j (字典序最小的必胜着法) 或 LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return 'LOSE'
    head = lines[idx].split()
    a, b = int(head[0]), int(head[1])
    lo, hi = (min(a, b), max(a, b))

    maxv = max(a, b)
    cold = [[False] * (maxv + 1) for _ in range(maxv + 1)]
    for t in range(maxv + 1):
        for u in range(t, maxv + 1):
            win = False
            i = 1
            while t - i >= 0:
                if not cold[t - i][u]:
                    win = True
                    break
                i += 1
            if not win:
                j = 1
                while u - j >= 0:
                    if not cold[t][u - j]:
                        win = True
                        break
                    j += 1
            if not win:
                d = 1
                while t - d >= 0 and u - d >= 0:
                    if not cold[t - d][u - d]:
                        win = True
                        break
                    d += 1
            cold[t][u] = not win

    if cold[lo][hi]:
        return 'LOSE'

    best = None
    i = 0
    while i <= a:
        j = 0
        while j <= b:
            if not (i == 0 and j == 0):
                na, nb = a - i, b - j
                if na <= nb:
                    canonical = (na, nb)
                else:
                    canonical = (nb, na)
                if cold[canonical[0]][canonical[1]]:
                    if best is None or (i, j) < best:
                        best = (i, j)
            j += 1
        i += 1
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
