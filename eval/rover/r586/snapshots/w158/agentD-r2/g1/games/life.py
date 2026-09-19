"""Conway's Game of Life: H W k then H rows of HxW grid; output grid after k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ''
        row = (row + '.' * w)[:w]
        grid.append([1 if c == '#' else 0 for c in row])
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
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = 1 if (cnt == 2 or cnt == 3) else 0
                else:
                    nxt[r][c] = 1 if cnt == 3 else 0
        grid = nxt
    return '\n'.join(''.join('#' if x else '.' for x in row) for row in grid)
