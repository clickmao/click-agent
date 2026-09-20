"""Conway's Game of Life: H W k, then H rows of W chars, evolve k generations."""


def _step(grid, h, w):
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny = y + dy
                    nx = x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
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
    if lines and lines[-1] == '':
        lines.pop()
    stripped = [ln.strip() for ln in lines]
    nonempty = [ln for ln in stripped if ln != '']
    if not nonempty:
        return ''
    h, w, k = (int(v) for v in nonempty[0].split()[:3])
    grid = []
    for ln in nonempty[1:]:
        grid.append(''.join(c for c in ln if c in '.#'))
        if len(grid) == h:
            break
    while len(grid) < h:
        grid.append('.' * w)
    grid = [row[:w].ljust(w, '.') for row in grid]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
