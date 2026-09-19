"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[i + 1]
        grid.append([1 if c == "#" else 0 for c in row[:w]])
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            n += grid[ny][nx]
                if grid[y][x]:
                    new[y][x] = 1 if (n == 2 or n == 3) else 0
                else:
                    new[y][x] = 1 if n == 3 else 0
        grid = new
    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
