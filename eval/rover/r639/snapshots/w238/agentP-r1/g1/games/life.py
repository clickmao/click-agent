def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        grid.append(list(lines[idx].rstrip('\n')))
        idx += 1

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == '#':
                    cnt += 1
        return cnt

    g = grid
    for _ in range(k):
        ng = [['.' for _ in range(W)] for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = neighbors(g, r, c)
                if g[r][c] == '#':
                    ng[r][c] = '#' if n in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if n == 3 else '.'
        g = ng
    return '\n'.join(''.join(row) for row in g)
