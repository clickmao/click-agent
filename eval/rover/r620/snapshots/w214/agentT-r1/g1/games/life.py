def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    parts = lines[idx].split()
    H, W, k = int(parts[0]), int(parts[1]), int(parts[2])
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx].strip()
        idx += 1
        cells = [c == "#" for c in row]
        if len(cells) < W:
            cells += [False] * (W - len(cells))
        grid.append(cells)
    for _ in range(k):
        ng = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx]:
                            n += 1
                if grid[y][x]:
                    ng[y][x] = n == 2 or n == 3
                else:
                    ng[y][x] = n == 3
        grid = ng
    out = []
    for row in grid:
        out.append("".join("#" if c else "." for c in row))
    return "\n".join(out)
