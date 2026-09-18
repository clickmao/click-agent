def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = [lines[idx + 1 + r][:w] for r in range(h)]
    alive = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] == "#":
                alive.add((r, c))
    for _ in range(k):
        cnt = {}
        for (r, c) in alive:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w:
                        cnt[(nr, nc)] = cnt.get((nr, nc), 0) + 1
        nxt = set()
        for (r, c), n in cnt.items():
            if n == 3 or (n == 2 and (r, c) in alive):
                nxt.add((r, c))
        alive = nxt
    return "\n".join(
        "".join("#" if (r, c) in alive else "." for c in range(w))
        for r in range(h)
    )
