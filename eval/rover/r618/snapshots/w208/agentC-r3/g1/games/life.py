def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i][:w].ljust(w, '.')) for i in range(h)]
    for _ in range(k):
        nxt = [['.' for _ in range(w)] for _ in range(h)]
        for r in range(h):
            for c in range(w):
                occ = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            occ += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if occ in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if occ == 3 else '.'
        grid = nxt
    return "\n".join("".join(row) for row in grid)
