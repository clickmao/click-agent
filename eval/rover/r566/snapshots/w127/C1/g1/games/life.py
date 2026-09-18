def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    rows = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and rows[ni][nj] == '#':
                            cnt += 1
                if rows[i][j] == '#':
                    new[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    new[i][j] = '#' if cnt == 3 else '.'
        rows = new
    return '\n'.join(''.join(r) for r in rows)
