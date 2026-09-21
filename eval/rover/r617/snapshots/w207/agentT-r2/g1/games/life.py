def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for row in lines[idx:idx + H]:
        cells = list(row)
        while len(cells) < W:
            cells.append('.')
        grid.append(cells[:W])
    cur = [[1 if c == '#' else 0 for c in row] for row in grid]
    for _ in range(k):
        nxt = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < H and 0 <= cc < W:
                            nb += cur[rr][cc]
                if cur[r][c]:
                    nxt[r][c] = 1 if (nb == 2 or nb == 3) else 0
                else:
                    nxt[r][c] = 1 if nb == 3 else 0
        cur = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in cur)
