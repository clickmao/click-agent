def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r].strip()] for r in range(h)]
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
                new[r][c] = (n == 3) or (grid[r][c] and n == 2)
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
