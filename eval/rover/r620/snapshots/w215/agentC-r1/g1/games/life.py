"""Conway's Game of Life: k 代同步演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = [list(lines[idx + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            nb += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if nb in (2, 3) else '.'
                else:
                    new[r][c] = '#' if nb == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
