def solve(text: str) -> str:
    lines = text.split("\n")
    it = iter(lines)
    first = next(it).split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for _ in range(h):
        row = next(it)
        grid.append([c == "#" for c in row[:w]])
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        grid = ng
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
