"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = lines[1:1 + h]
    grid = [[1 if ch == "#" else 0 for ch in row] for row in rows]
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            cnt += grid[ny][nx]
                if grid[y][x]:
                    nxt[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[y][x] = 1 if cnt == 3 else 0
        grid = nxt
    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
