"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i][:w]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
