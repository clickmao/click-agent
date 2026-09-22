"""Conway's Game of Life: evolve the grid H rows by W cols for k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(row[:w])

    for _ in range(k):
        nxt = []
        for y in range(h):
            out = []
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            cnt += 1
                if grid[y][x] == "#":
                    out.append("#" if cnt == 2 or cnt == 3 else ".")
                else:
                    out.append("#" if cnt == 3 else ".")
            nxt.append("".join(out))
        grid = nxt

    return "\n".join(grid)
