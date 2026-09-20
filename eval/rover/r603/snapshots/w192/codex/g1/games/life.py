def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while not lines[idx].strip():
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        grid.append(list(lines[idx + r].strip()))
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
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
                if alive and cnt in (2, 3):
                    new[r][c] = '#'
                elif not alive and cnt == 3:
                    new[r][c] = '#'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
