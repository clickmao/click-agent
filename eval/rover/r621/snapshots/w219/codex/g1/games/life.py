def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
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
                    key = (r + dr, c + dc)
                    counts[key] = counts.get(key, 0) + 1
        new_grid = set()
        for (r, c), cnt in counts.items():
            if cnt == 3 or (cnt == 2 and (r, c) in grid):
                if 0 <= r < h and 0 <= c < w:
                    new_grid.add((r, c))
        grid = new_grid
    out = []
    for r in range(h):
        out.append(''.join('#' if (r, c) in grid else '.' for c in range(w)))
    return '\n'.join(out)
