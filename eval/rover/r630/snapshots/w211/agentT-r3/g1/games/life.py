def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i].strip()
        grid.append([c == '#' for c in row])
    cur = grid
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and cur[nr][nc]:
                            cnt += 1
                if cur[r][c]:
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        cur = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in cur)
