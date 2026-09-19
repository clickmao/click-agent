"""Conway's Game of Life: evolve the grid k generations."""


def _step(grid, h, w):
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            alive = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny = y + dy
                    nx = x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                        alive += 1
            if grid[y][x] == '#':
                row.append('#' if alive in (2, 3) else '.')
            else:
                row.append('#' if alive == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text):
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < h and idx < len(lines):
        line = lines[idx]
        idx += 1
        if line == '' and len(grid) >= 0:
            pass
        if len(line) >= w:
            grid.append(line[:w])
        elif line.strip() == '' and len(grid) == 0:
            continue
        else:
            grid.append((line + '.' * w)[:w])
    while len(grid) < h:
        grid.append('.' * w)
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
