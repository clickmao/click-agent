"""Conway's Game of Life evolution."""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = set()
    for r in range(h):
        row = lines[1 + r]
        for c in range(w):
            if row[c] == '#':
                grid.add((r, c))
    for _ in range(k):
        counts = {}
        for (r, c) in grid:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    p = (r + dr, c + dc)
                    counts[p] = counts.get(p, 0) + 1
        new = set()
        for (r, c), n in counts.items():
            if 0 <= r < h and 0 <= c < w:
                if (r, c) in grid:
                    if n == 2 or n == 3:
                        new.add((r, c))
                else:
                    if n == 3:
                        new.add((r, c))
        grid = new
    out = []
    for r in range(h):
        out.append(''.join('#' if (r, c) in grid else '.' for c in range(w)))
    return '\n'.join(out)
