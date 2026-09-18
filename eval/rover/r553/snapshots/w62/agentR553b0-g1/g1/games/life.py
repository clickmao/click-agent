"""Conway's Game of Life: k generations of a HxW grid."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w].ljust(w, '.')) for i in range(h)]

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
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
                    nxt[r][c] = '#'
                elif not alive and n == 3:
                    nxt[r][c] = '#'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
