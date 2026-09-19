def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[c == '#' for c in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
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
                if grid[r][c]:
                    new[r][c] = n == 2 or n == 3
                else:
                    new[r][c] = n == 3
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
