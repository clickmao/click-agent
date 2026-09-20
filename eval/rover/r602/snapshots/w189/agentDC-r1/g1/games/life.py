"""Conway's Game of Life: evolve H x W grid by k generations."""


def solve(text: str) -> str:
    nums = []
    lines = []
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]

    first = lines[0].split()
    h, w = int(first[0]), int(first[1])
    k = int(first[2])
    row_lines = lines[1:1 + h]
    grid = []
    for r in range(h):
        row = row_lines[r] if r < len(row_lines) else ''
        cells = [1 if (c < len(row) and row[c] == '#') else 0 for c in range(w)]
        grid.append(cells)

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            nb += grid[rr][cc]
                if grid[r][c]:
                    nxt[r][c] = 1 if (nb == 2 or nb == 3) else 0
                else:
                    nxt[r][c] = 1 if nb == 3 else 0
        grid = nxt

    out = []
    for r in range(h):
        out.append(''.join('#' if grid[r][c] else '.' for c in range(w)))
    return '\n'.join(out)
