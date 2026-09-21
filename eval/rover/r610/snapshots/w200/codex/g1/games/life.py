def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]

    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            alive += 1
                cell = grid[r][c]
                if cell == '#':
                    new[r][c] = '#' if alive in (2, 3) else '.'
                else:
                    new[r][c] = '#' if alive == 3 else '.'
        grid = new

    return '\n'.join(''.join(row) for row in grid)
