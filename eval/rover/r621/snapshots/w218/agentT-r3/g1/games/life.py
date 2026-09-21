def solve(text):
    data = text.split()
    h = int(data[0])
    w = int(data[1])
    k = int(data[2])
    rows = data[3:3 + h]
    alive = set()
    for y in range(h):
        row = rows[y]
        for x in range(w):
            if row[x] == '#':
                alive.add((y, x))
    for _ in range(k):
        counts = {}
        for (y, x) in alive:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    p = (y + dy, x + dx)
                    counts[p] = counts.get(p, 0) + 1
        nxt = set()
        for (y, x) in alive:
            c = counts.get((y, x), 0)
            if c == 2 or c == 3:
                nxt.add((y, x))
        for (y, x), c in counts.items():
            if c == 3 and (y, x) not in alive:
                nxt.add((y, x))
        alive = nxt
    out = []
    for y in range(h):
        out.append(''.join('#' if (y, x) in alive else '.' for x in range(w)))
    return '\n'.join(out)
