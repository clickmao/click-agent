def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    lose = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            any_move = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    any_move = True
                    break
            if not any_move:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        any_move = True
                        break
            if not any_move:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        any_move = True
                        break
            lose[i][j] = not any_move
    if lose[a][b]:
        return 'LOSE'
    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i > 0 and j > 0 and i == j):
                if lose[a - i][b - j]:
                    candidates.append((i, j))
    candidates.sort()
    i, j = candidates[0]
    return 'WIN ' + str(i) + ' ' + str(j)
