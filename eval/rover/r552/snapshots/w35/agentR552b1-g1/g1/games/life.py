def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                ng[r][c] = (n == 3) if not grid[r][c] else (n == 2 or n == 3)
        grid = ng
    return '\n'.join(''.join('#' if x else '.' for x in row) for row in grid)
