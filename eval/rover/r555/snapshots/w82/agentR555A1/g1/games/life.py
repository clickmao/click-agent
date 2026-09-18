def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    g = []
    for _ in range(h):
        row = lines[idx].rstrip('\n')
        idx += 1
        row = (row + '.' * w)[:w]
        g.append(row)
    for _ in range(k):
        ng = []
        for r in range(h):
            out = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    out.append('#' if cnt == 2 or cnt == 3 else '.')
                else:
                    out.append('#' if cnt == 3 else '.')
            ng.append(''.join(out))
        g = ng
    return '\n'.join(g)
