def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    cells = set()
    for r in range(h):
        row = lines[1 + r]
        for c in range(w):
            if row[c] == '#':
                cells.add((r, c))
    for _ in range(k):
        nxt = set()
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if (r + dr, c + dc) in cells:
                            cnt += 1
                if (r, c) in cells:
                    if cnt == 2 or cnt == 3:
                        nxt.add((r, c))
                else:
                    if cnt == 3:
                        nxt.add((r, c))
        cells = nxt
    out = []
    for r in range(h):
        out.append(''.join('#' if (r, c) in cells else '.' for c in range(w)))
    return '\n'.join(out)
