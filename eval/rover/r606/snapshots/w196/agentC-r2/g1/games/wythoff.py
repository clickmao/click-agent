def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    N = 26
    losing = [[False] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i == 0 and j == 0:
                losing[i][j] = True
                continue
            is_lose = True
            for take in range(1, i + 1):
                if losing[i - take][j]:
                    is_lose = False
                    break
            if is_lose:
                for take in range(1, j + 1):
                    if losing[i][j - take]:
                        is_lose = False
                        break
            if is_lose:
                t = 1
                while t <= i and t <= j:
                    if losing[i - t][j - t]:
                        is_lose = False
                        break
                    t += 1
            losing[i][j] = is_lose
    if losing[a][b]:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing[a - i][b - j]:
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
