def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    # losing[x][y] == True  <=>  局面 (min(x,y), max(x,y)) 是先手必败
    losing = [[False] * 26 for _ in range(26)]
    for x in range(26):
        for y in range(26):
            if x == 0 and y == 0:
                losing[x][y] = True
                continue
            win = False
            for i in range(1, x + 1):
                if losing[x - i][y]:
                    win = True
                    break
            if not win:
                for j in range(1, y + 1):
                    if losing[x][y - j]:
                        win = True
                        break
            if not win:
                for d in range(1, min(x, y) + 1):
                    if losing[x - d][y - d]:
                        win = True
                        break
            losing[x][y] = not win

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        return losing[x][y]

    if is_losing(a, b):
        return 'LOSE'

    # 按 (i, j) 字典序寻找能走到必败态的最小必胜着法
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue  # 非法: 不能只从某一堆取, 且两堆取的数目必须相等
            if is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
