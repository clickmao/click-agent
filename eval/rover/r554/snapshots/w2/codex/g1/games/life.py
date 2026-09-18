def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [line[:w] for line in lines[1:1 + h]]
    for _ in range(k):
        new = []
        for r in range(h):
            row = []
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                alive = grid[r][c] == '#'
                if n == 3 or (alive and n == 2):
                    row.append('#')
                else:
                    row.append('.')
            new.append(''.join(row))
        grid = new
    return '\n'.join(grid)
