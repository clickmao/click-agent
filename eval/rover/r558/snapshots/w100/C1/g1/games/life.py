def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    def step(g):
        ng = []
        for r in range(h):
            row = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            ng.append(row)
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
