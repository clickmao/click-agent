def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    parts = lines[idx].split()
    h, w, k = (int(x) for x in parts[:3])
    rows = lines[idx + 1:idx + 1 + h]
    grid = [[1 if c == '#' else 0 for c in row[:w]] for row in rows]
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    ng[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    ng[r][c] = 1 if cnt == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
