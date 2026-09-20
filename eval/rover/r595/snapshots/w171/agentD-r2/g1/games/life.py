def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]
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
                nxt[r][c] = (grid[r][c] and cnt in (2, 3)) or ((not grid[r][c]) and cnt == 3)
        grid = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
