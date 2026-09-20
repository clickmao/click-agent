def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split())
    g = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        ng = [['.' for _ in range(w)] for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and g[ni][nj] == '#':
                            cnt += 1
                if g[i][j] == '#':
                    ng[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[i][j] = '#' if cnt == 3 else '.'
        g = ng
    return '\n'.join(''.join(row) for row in g)
