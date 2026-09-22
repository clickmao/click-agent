"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append([row[j] if j < len(row) and row[j] == '#' else '.' for j in range(w)])

    def step(g):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    ng[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if cnt == 3 else '.'
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
