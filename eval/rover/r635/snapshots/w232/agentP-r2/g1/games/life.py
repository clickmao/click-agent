def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    cells = {}
    for y in range(h):
        row = lines[1 + y]
        for x in range(w):
            cells[(x, y)] = row[x] == '#'
    for _ in range(k):
        new = {}
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        if cells.get((x + dx, y + dy), False):
                            n += 1
                if cells[(x, y)]:
                    new[(x, y)] = n == 2 or n == 3
                else:
                    new[(x, y)] = n == 3
        cells = new
    out = []
    for y in range(h):
        out.append(''.join('#' if cells[(x, y)] else '.' for x in range(w)))
    return '\n'.join(out)
