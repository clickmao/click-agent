def solve(text: str) -> str:
    lines = text.splitlines()

    def nxt():
        for i in range(len(lines)):
            s = lines[i]
            if s.strip():
                yield i, s

    it = nxt()
    _, header = next(it)
    H, W, k = map(int, header.split())
    grid = []
    for _ in range(H):
        _, row = next(it)
        grid.append(list(row[:W]))
    for _ in range(k):
        new = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if n in (2, 3) else '.'
                else:
                    new[r][c] = '#' if n == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
