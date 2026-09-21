def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip()
        idx += 1
        grid.append(row)
    for _ in range(k):
        new = []
        for r in range(h):
            out = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            cnt += 1
                alive = grid[r][c] == '#'
                if alive:
                    out.append('#' if cnt in (2, 3) else '.')
                else:
                    out.append('#' if cnt == 3 else '.')
            new.append(''.join(out))
        grid = new
    return '\n'.join(grid)
