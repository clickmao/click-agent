def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i].ljust(w, '.')[:w]) for i in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
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
                    nxt[r][c] = '#'
                elif not alive and cnt == 3:
                    nxt[r][c] = '#'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
