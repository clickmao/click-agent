def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(1, h + 1):
        row = lines[i] if i < len(lines) else ''
        cells = [1 if c == '#' else 0 for c in row[:w]]
        while len(cells) < w:
            cells.append(0)
        grid.append(cells)

    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            nb += 1
                if grid[r][c]:
                    new[r][c] = 1 if nb in (2, 3) else 0
                else:
                    new[r][c] = 1 if nb == 3 else 0
        grid = new

    return '\n'.join(''.join('#' if x else '.' for x in row) for row in grid)
