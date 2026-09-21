"""Conway's Game of Life: evolve k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split()[:3])
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i]
        cells = [1 if row[j] == '#' else 0 for j in range(w)]
        grid.append(cells)

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            alive += 1
                if grid[r][c]:
                    nxt[r][c] = 1 if (alive == 2 or alive == 3) else 0
                else:
                    nxt[r][c] = 1 if alive == 3 else 0
        grid = nxt

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
