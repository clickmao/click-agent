"""Conway's Game of Life: k generations on an H x W grid."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == '#':
                    cnt += 1
        return cnt

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

    return '\n'.join(''.join(row) for row in grid)
