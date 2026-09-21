"""Conway's Game of Life: evolve k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h_str, w_str, k_str = lines[idx].split()
    idx += 1
    h = int(h_str)
    w = int(w_str)
    k = int(k_str)
    rows = []
    while len(rows) < h and idx < len(lines):
        line = lines[idx].rstrip('\r')
        idx += 1
        if line == '':
            continue
        rows.append(line.ljust(w, '.'))
    grid = [list(row) for row in rows]

    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if n in (2, 3) else '.'
                else:
                    new[r][c] = '#' if n == 3 else '.'
        grid = new

    return '\n'.join(''.join(row) for row in grid)
