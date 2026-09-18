"""Conway's Game of Life evolution."""


def _evolve(cells, h, w):
    live = set(cells)
    new = set()
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    if (r + dr, c + dc) in live:
                        n += 1
            if (r, c) in live:
                if n == 2 or n == 3:
                    new.add((r, c))
            else:
                if n == 3:
                    new.add((r, c))
    return new


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split()[:3])
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([(1 if ch == '#' else 0) for ch in row[:w]])
    cells = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c]:
                cells.add((r, c))
    for _ in range(k):
        cells = _evolve(cells, h, w)
    out = []
    for r in range(h):
        out.append(''.join('#' if (r, c) in cells else '.' for c in range(w)))
    return '\n'.join(out)
