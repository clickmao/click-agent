def solve(text):
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    H, W, k = map(int, lines[idx].split())
    grid = []
    for i in range(H):
        row = lines[idx + 1 + i].rstrip()
        grid.append([c == "#" for c in row[:W]])

    for _ in range(k):
        new = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    new[y][x] = cnt == 2 or cnt == 3
                else:
                    new[y][x] = cnt == 3
        grid = new

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
