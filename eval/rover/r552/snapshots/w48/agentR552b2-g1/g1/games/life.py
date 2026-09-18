def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]

    def step(g):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc]:
                            cnt += 1
                if g[r][c]:
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join('#' if x else '.' for x in row) for row in grid)
