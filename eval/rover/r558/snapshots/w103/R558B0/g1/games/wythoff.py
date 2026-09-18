"""Game: Wythoff (remove from one pile, or equal amounts from both; last stone wins)."""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    maxv = 25
    P = [[False] * (maxv + 1) for _ in range(maxv + 1)]
    for x in range(maxv + 1):
        for y in range(maxv + 1):
            if x == 0 and y == 0:
                P[x][y] = True
                continue
            losing = False
            i = 1
            while x - i >= 0:
                if P[x - i][y]:
                    losing = True
                    break
                i += 1
            if not losing:
                j = 1
                while y - j >= 0:
                    if P[x][y - j]:
                        losing = True
                        break
                    j += 1
            if not losing:
                d = 1
                while x - d >= 0 and y - d >= 0:
                    if P[x - d][y - d]:
                        losing = True
                        break
                    d += 1
            P[x][y] = losing

    if P[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if P[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
