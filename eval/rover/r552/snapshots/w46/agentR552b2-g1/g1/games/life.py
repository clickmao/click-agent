def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()
    head = lines[0].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    rows = lines[1:1 + h]
    grid = []
    for r in range(h):
        row = rows[r].ljust(w, '.')
        grid.append([c == '#' for c in row[:w]])
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
