"""Wythoff game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    n = max(a, b)

    lose = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            is_lose = True
            for x in range(i):
                if lose[x][j]:
                    is_lose = False
                    break
            if is_lose:
                for y in range(j):
                    if lose[i][y]:
                        is_lose = False
                        break
            if is_lose:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        is_lose = False
                        break
            lose[i][j] = is_lose

    def is_lose(x, y):
        if x <= y:
            return lose[x][y]
        return lose[y][x]

    if is_lose(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
