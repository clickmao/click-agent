"""Conway's Game of Life: H x W grid, k generations."""


def _step(cells, H, W):
    out = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and cells[rr][cc]:
                        n += 1
            alive = cells[r][c]
            if alive:
                row.append(n == 2 or n == 3)
            else:
                row.append(n == 3)
        out.append(row)
    return out


def solve(text):
    lines = text.splitlines()
    H, W, k = (int(x) for x in lines[0].split()[:3])
    cells = [[ch == '#' for ch in lines[1 + r][:W]] for r in range(H)]
    for _ in range(k):
        cells = _step(cells, H, W)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in cells)
