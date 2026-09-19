"""Conway's Game of Life: evolve k generations on an H x W grid."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(t) for t in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        nxt = []
        for r in range(h):
            row = []
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
                    row.append('#' if n in (2, 3) else '.')
                else:
                    row.append('#' if n == 3 else '.')
            nxt.append(row)
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
