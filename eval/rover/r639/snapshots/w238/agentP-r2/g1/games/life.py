"""Conway's Game of Life: evolve H x W board k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = [lines[1 + i] for i in range(h)]
    grid = [[c == '#' for c in rows[i]] for i in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            nb += 1
                if grid[r][c]:
                    nxt[r][c] = nb == 2 or nb == 3
                else:
                    nxt[r][c] = nb == 3
        grid = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
