def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\r")
        idx += 1
        grid.append([c == "#" for c in row])

    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    new[y][x] = cnt == 2 or cnt == 3
                else:
                    new[y][x] = cnt == 3
        grid = new

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
