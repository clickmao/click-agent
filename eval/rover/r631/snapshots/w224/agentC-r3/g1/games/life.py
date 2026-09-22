def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    g = []
    for i in range(h):
        g.append(list(lines[idx + i].strip()))
    for _ in range(k):
        ng = []
        for i in range(h):
            row = []
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < h and 0 <= nj < w and g[ni][nj] == '#':
                            cnt += 1
                if g[i][j] == '#':
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            ng.append(''.join(row))
        g = ng
    return '\n'.join(''.join(r) for r in g)
