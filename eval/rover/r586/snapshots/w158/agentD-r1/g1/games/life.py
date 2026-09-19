"""Conway's Game of Life: evolve a grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    header = lines[idx].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    idx += 1
    grid = []
    while len(grid) < h:
        row = lines[idx]
        idx += 1
        if row == "" and len(grid) < h:
            row = "." * w
        row = (row + "." * w)[:w]
        grid.append(row)

    live = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] == "#":
                live.add((r, c))

    for _ in range(k):
        counts = {}
        for (r, c) in live:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    pos = (r + dr, c + dc)
                    counts[pos] = counts.get(pos, 0) + 1
        nxt = set()
        for pos, n in counts.items():
            r, c = pos
            if 0 <= r < h and 0 <= c < w:
                if n == 3 or (n == 2 and pos in live):
                    nxt.add(pos)
        live = nxt

    out = []
    for r in range(h):
        out.append("".join("#" if (r, c) in live else "." for c in range(w)))
    return "\n".join(out)
