"""Conway's Game of Life: evolve H x W grid for k generations."""


def evolve(grid, h, w):
    """Return the next generation of the grid (list of strings)."""
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                ny = y + dy
                if 0 <= ny < h:
                    src = grid[ny]
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        if 0 <= nx < w and src[nx] == '#':
                            n += 1
            alive = grid[y][x] == '#'
            if alive:
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(v) for v in lines[0].split())
    grid = [lines[1 + i][:w] for i in range(h)]
    for _ in range(k):
        grid = evolve(grid, h, w)
    return '\n'.join(grid)
