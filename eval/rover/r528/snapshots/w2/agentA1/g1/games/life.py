"""Conway's Game of Life: evolve the grid for k generations."""


def _evolve(cells, h, w):
    """One simultaneous generation step with out-of-grid cells treated as dead."""
    nxt = [['.' for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            alive = 0
            for dy in (-1, 0, 1):
                ny = y + dy
                if ny < 0 or ny >= h:
                    continue
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    if 0 <= nx < w and cells[ny][nx] == '#':
                        alive += 1
            if cells[y][x] == '#':
                nxt[y][x] = '#' if (alive == 2 or alive == 3) else '.'
            else:
                nxt[y][x] = '#' if alive == 3 else '.'
    return nxt


def solve(text: str) -> str:
    """Parse 'H W k' + H rows, evolve k times, return the resulting grid."""
    lines = text.splitlines()
    h, w, k = (int(v) for v in lines[0].split()[:3])
    grid = []
    for i in range(1, h + 1):
        row = lines[i] if i < len(lines) else ''
        row = (row + '.' * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        grid = _evolve(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
