"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    rows = []
    while len(rows) < h and idx < len(lines):
        row = lines[idx]
        idx += 1
        if len(row) < w:
            row = row + '.' * (w - len(row))
        rows.append(row[:w])
    while len(rows) < h:
        rows.append('.' * w)

    grid = [[1 if ch == '#' else 0 for ch in row] for row in rows]

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            cnt += grid[nr][nc]
                if grid[r][c]:
                    nxt[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if cnt == 3 else 0
        grid = nxt

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
