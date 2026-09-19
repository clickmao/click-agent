def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    # losing(a,b) iff (a,b) 是必败点; 先手必败条件: a==b 时 a 为 P-position 分量
    # 用 DP 直接判定, 规模 <= 25 足够
    # 状态排序: 剩余 (x,y), x<=y 归一化
    # losing[x][y]: x<=y
    losing = [[False] * (26) for _ in range(26)]
    # 从大到小枚举不可能, 改用从小到大: (0,0) 为必败
    for x in range(0, 26):
        for y in range(x, 26):
            if x == 0 and y == 0:
                losing[x][y] = True
                continue
            # 存在必胜着法 <=> 有一个后继是必败态
            ok = False
            # (i) 从第一堆取 t
            for t in range(1, x + 1):
                nx, ny = x - t, y
                if nx > ny:
                    nx, ny = ny, nx
                if losing[nx][ny]:
                    ok = True
                    break
            if not ok:
                for t in range(1, y + 1):
                    nx, ny = x, y - t
                    if nx < 0:
                        nx, ny = nx, ny
                    if nx > ny:
                        nx, ny = ny, nx
                    if losing[nx][ny]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(x, y) + 1):
                    nx, ny = x - t, y - t
                    if nx > ny:
                        nx, ny = ny, nx
                    if losing[nx][ny]:
                        ok = True
                        break
            losing[x][y] = not ok
    x, y = (a, b) if a <= b else (b, a)
    if losing[x][y]:
        return "LOSE"
    # 找字典序最小的必胜着法 (i,j): 对原 (a,b), 新状态必败
    def is_losing(nx, ny):
        if nx > ny:
            nx, ny = ny, nx
        return losing[nx][ny]
    candidates = []
    # 类型(i): 从第一堆取 i>0
    for i in range(0, a + 1):
        j = 0
        if i == 0:
            continue
        if is_losing(a - i, b):
            candidates.append((i, j))
    # 类型(i): 从第二堆取 j>0
    for j in range(1, b + 1):
        if is_losing(a, b - j):
            candidates.append((0, j))
    # 类型(ii): 同时取 t>0
    for t in range(1, min(a, b) + 1):
        if is_losing(a - t, b - t):
            candidates.append((t, t))
    i, j = min(candidates)
    return "WIN %d %d" % (i, j)
