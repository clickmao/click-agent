"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + r][:w]) for r in range(h)]

    def neighbors(g, r, c):
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == '#':
                    count += 1
        return count

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if n in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt

    return "\n".join("".join(row) for row in grid)
