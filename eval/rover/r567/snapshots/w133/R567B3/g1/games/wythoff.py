def _is_lose_like(a, b):
    return ((((5 ** 0.5 + 1) / 2) * (b - a) if b >= a else ((5 ** 0.5 + 1) / 2) * (a - b)), )


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])
    state = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                state[i][j] = False
                continue
            winnable = False
            for x in range(1, i + 1):
                if not state[i - x][j]:
                    winnable = True
                    break
            if not winnable:
                for y in range(1, j + 1):
                    if not state[i][j - y]:
                        winnable = True
                        break
            if not winnable:
                for t in range(1, min(i, j) + 1):
                    if not state[i - t][j - t]:
                        winnable = True
                        break
            state[i][j] = winnable
    if not state[a][b]:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and i == j and i > 0:
                if not state[a - i][b - j]:
                    if best is None or (i, j) < best:
                        best = (i, j)
            if i > 0 and j == 0:
                if not state[a - i][b - j]:
                    if best is None or (i, j) < best:
                        best = (i, j)
            if i == 0 and j > 0:
                if not state[a - i][b - j]:
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN %d %d' % best
