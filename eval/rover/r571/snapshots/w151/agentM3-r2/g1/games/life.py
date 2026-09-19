"""Conway's Game of Life: evolve the grid for k generations."""


def solve(text: str) -> str:
    lines = text.split(chr(10))
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ''
        row = (row + '.' * w)[:w]
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
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                nxt[r][c] = (cnt == 3) or (grid[r][c] and cnt == 2)
        grid = nxt
    return chr(10).join(''.join('#' if v else '.' for v in row) for row in grid)
