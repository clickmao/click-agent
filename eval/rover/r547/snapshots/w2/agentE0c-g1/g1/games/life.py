"""Conway's Game of Life: evolve HxW grid k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and rows[ny][nx] == '#':
                            n += 1
                if rows[y][x] == '#':
                    new[y][x] = '#' if n in (2, 3) else '.'
                else:
                    new[y][x] = '#' if n == 3 else '.'
        rows = new
    return '\n'.join(''.join(r) for r in rows)
