def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i].strip()) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                alive = grid[r][c] == '#'
                if alive and n in (2, 3):
                    new[r][c] = '#'
                elif not alive and n == 3:
                    new[r][c] = '#'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
