"""Conway's Game of Life: evolve the grid k generations."""

NEIGHBORS = ((-1, -1), (-1, 0), (-1, 1),
             (0, -1), (0, 1),
             (1, -1), (1, 0), (1, 1))


def _split_lines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def solve(text: str) -> str:
    lines = _split_lines(text)
    h, w, k = (int(x) for x in lines[0].split())
    rows = []
    for i in range(h):
        line = lines[1 + i] if 1 + i < len(lines) else ""
        line = line.rstrip()
        if len(line) < w:
            line = line + "." * (w - len(line))
        rows.append(line[:w])

    grid = [[c == "#" for c in row] for row in rows]

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr, dc in NEIGHBORS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                        alive += 1
                if grid[r][c]:
                    nxt[r][c] = alive == 2 or alive == 3
                else:
                    nxt[r][c] = alive == 3
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
