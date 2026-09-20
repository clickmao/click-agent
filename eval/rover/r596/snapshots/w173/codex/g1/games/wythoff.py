def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    losing = [[False] * 26 for _ in range(26)]
    for i in range(26):
        for j in range(26):
            if i == 0 and j == 0:
                losing[i][j] = True
                continue
            ok = False
            for t in range(1, i + 1):
                if losing[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if losing[i][j - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(i, j) + 1):
                    if losing[i - t][j - t]:
                        ok = True
                        break
            losing[i][j] = not ok

    if losing[a][b]:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if losing[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
