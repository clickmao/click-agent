"""Conway's Game of Life: k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append([row[j] for j in range(w)])
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
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
                    ng[r][c] = '#'
                elif (not alive) and n == 3:
                    ng[r][c] = '#'
        grid = ng
    return '\n'.join(''.join(row) for row in grid)
